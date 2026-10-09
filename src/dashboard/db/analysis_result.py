"""CRUD helpers for the daily_analysis_result table"""

import os
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session, selectinload

from dashboard.db.crud import CRUDBase

from . import utils
from .data_model import (
    ClassificationCorrection,
    DailyAnalysisResult,
    DetectionCorrection,
    ImageCapture,
    ObjectDetection,
    SpeciesClassification,
)

# timezone in which a day starts and ends, i.e. the timezone of the cameras
ANALYSIS_TZ = os.getenv("ANALYSIS_TZ", "Asia/Colombo")

# confidence of a species set by a user correction
CORRECTED_CONFIDENCE = 1.0


def _zone(tz: str | ZoneInfo | None) -> ZoneInfo:
    if tz is None:
        tz = ANALYSIS_TZ
    return tz if isinstance(tz, ZoneInfo) else ZoneInfo(tz)


def day_bounds(
    day: date, tz: str | ZoneInfo | None = None
) -> tuple[datetime, datetime]:
    """Return the start (inclusive) and end (exclusive) of a day in a timezone.
    tz defaults to ANALYSIS_TZ."""

    zone = _zone(tz)
    start = datetime.combine(day, time.min, tzinfo=zone)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)
    return start, end


def _lock_day(session: Session, day: date) -> None:
    """Wait until no other transaction aggregates the same day,
    then hold the lock until the current transaction ends."""

    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext('daily_analysis_result'), :day)"),
        {"day": day.toordinal()},
    )


def _latest[Correction: (DetectionCorrection, ClassificationCorrection)](
    corrections: list[Correction],
) -> Correction | None:
    """Return the correction with the latest last_updated, or None if there is none.
    Corrections of different users on the same item compete; ties go to the newest row.
    """

    return max(corrections, key=lambda c: (c.last_updated, c.id), default=None)


def _detection_species(detection: ObjectDetection) -> tuple[int, float] | None:
    """Return (taxonomy_id, confidence) of a model detection after user corrections,
    or None if the detection was removed or has no species."""

    correction = _latest(detection.detection_corrections)
    if correction is not None and correction.action == "remove":
        return None

    classification_correction = _latest(
        [
            correction
            for classification in detection.species_classifications
            for correction in classification.classification_corrections
        ]
    )
    if classification_correction is not None:
        return classification_correction.corrected_taxonomy_id, CORRECTED_CONFIDENCE

    # the most confident classification wins, also across classification models
    top = max(
        detection.species_classifications,
        key=lambda classification: classification.confidence,
        default=None,
    )
    if top is None:
        return None
    return top.taxonomy_id, top.confidence


def _added_detection_species(
    correction: DetectionCorrection,
) -> tuple[int, float] | None:
    """Return (taxonomy_id, confidence) of a detection added by a user,
    or None if it was removed again or has no species."""

    if correction.action == "remove":
        return None

    classification_correction = _latest(correction.classification_corrections)
    if classification_correction is None:
        return None
    return classification_correction.corrected_taxonomy_id, CORRECTED_CONFIDENCE


def _image_species(image: ImageCapture) -> list[tuple[int, float]]:
    """Return (taxonomy_id, confidence) of every detection in an image
    that has a species after user corrections."""

    # detections of different models can't be matched to each other,
    # so the same animal would be counted once per model
    det_model_ids = {detection.det_model_id for detection in image.object_detections}
    if len(det_model_ids) > 1:
        raise ValueError(
            f"Image {image.image_path} has detections of several detection models "
            f"{sorted(det_model_ids)}, which the daily analysis does not support."
        )

    species = [_detection_species(detection) for detection in image.object_detections]
    species += [
        _added_detection_species(correction)
        for correction in image.detection_corrections
        if correction.new_detection_id is not None
    ]
    return [item for item in species if item is not None]


class DailyAnalysisResultCRUD(CRUDBase[DailyAnalysisResult]):
    """CRUD helpers for the daily_analysis_result table"""

    def __init__(self):
        super().__init__(DailyAnalysisResult)

    def compute_daily_results(
        self,
        session: Session,
        day: date,
        tz: str | ZoneInfo | None = None,
        *,
        camera_id: int | None = None,
        recompute: bool = False,
        commit: bool = True,
    ) -> list[DailyAnalysisResult]:
        """Aggregate the detections of the images captured on a day into
        daily_analysis_result, one row per camera and taxonomy,
        and mark the images as tobe_deleted.

        The day runs from midnight to midnight in tz (defaults to ANALYSIS_TZ).
        User corrections override the model results; per item, the latest one wins.

        By default, only images not aggregated yet (tobe_deleted is False) are used,
        and their counts are merged into the existing rows of the day.
        With recompute=True, all images of the day are used and the rows of the day
        are rebuilt. This is refused if an image was already moved out of the watch
        folder, since the results of moved images might be gone.

        With commit=False, the changes are only flushed, so the caller can commit
        them together with other changes (e.g. the correction that caused them).

        Returns the rows of the day (of camera_id, if given).
        """

        start, end = day_bounds(day, tz)
        try:
            self._aggregate(session, day, start, end, camera_id, recompute)
        except Exception:
            if commit:
                session.rollback()
            raise

        if commit:
            utils.commit(session)
        return self._day_rows(session, start, camera_id)

    def _aggregate(
        self,
        session: Session,
        day: date,
        start: datetime,
        end: datetime,
        camera_id: int | None,
        recompute: bool,
    ) -> None:
        _lock_day(session, day)

        statement = (
            select(ImageCapture)
            .where(ImageCapture.captured_at >= start, ImageCapture.captured_at < end)
            .options(
                selectinload(ImageCapture.object_detections).selectinload(
                    ObjectDetection.detection_corrections
                ),
                selectinload(ImageCapture.object_detections)
                .selectinload(ObjectDetection.species_classifications)
                .selectinload(SpeciesClassification.classification_corrections),
                selectinload(ImageCapture.detection_corrections).selectinload(
                    DetectionCorrection.classification_corrections
                ),
            )
            # reload rows already in the session, e.g. a correction just flushed
            .execution_options(populate_existing=True)
        )
        if camera_id is not None:
            statement = statement.where(ImageCapture.camera_id == camera_id)
        if not recompute:
            statement = statement.where(ImageCapture.tobe_deleted.is_(False))
        images = list(session.scalars(statement).all())

        existing_rows = self._day_rows(session, start, camera_id)
        if recompute:
            moved = [image.image_path for image in images if image.is_moved]
            if moved:
                raise ValueError(
                    f"Cannot recompute {day}: {len(moved)} image(s) were already moved "
                    f"out of the watch folder, e.g. {moved[0]}"
                )
            if not images and existing_rows:
                raise ValueError(
                    f"Cannot recompute {day}: the images of its results are gone."
                )

        # (camera_id, taxonomy_id) -> [count, sum of confidences]
        totals: defaultdict[tuple[int, int], list[float]] = defaultdict(
            lambda: [0, 0.0]
        )
        for image in images:
            for taxonomy_id, confidence in _image_species(image):
                total = totals[(image.camera_id, taxonomy_id)]
                total[0] += 1
                total[1] += confidence

        if recompute:
            statement = delete(DailyAnalysisResult).where(
                DailyAnalysisResult.start_time == start
            )
            if camera_id is not None:
                statement = statement.where(DailyAnalysisResult.camera_id == camera_id)
            session.execute(statement)
            existing_rows = []

        rows = {(row.camera_id, row.taxonomy_id): row for row in existing_rows}
        for (image_camera_id, taxonomy_id), (count, confidence_sum) in totals.items():
            row = rows.get((image_camera_id, taxonomy_id))
            if row is None:
                session.add(
                    DailyAnalysisResult(
                        camera_id=image_camera_id,
                        start_time=start,
                        end_time=end,
                        taxonomy_id=taxonomy_id,
                        taxonomy_count=count,
                        avg_confidence=confidence_sum / count,
                    )
                )
            else:
                # merge late images into the existing row
                merged_count = row.taxonomy_count + count
                row.avg_confidence = (
                    row.avg_confidence * row.taxonomy_count + confidence_sum
                ) / merged_count
                row.taxonomy_count = merged_count

        for image in images:
            image.tobe_deleted = True
        session.flush()

    def _day_rows(
        self, session: Session, start: datetime, camera_id: int | None
    ) -> list[DailyAnalysisResult]:
        statement = select(DailyAnalysisResult).where(
            DailyAnalysisResult.start_time == start
        )
        if camera_id is not None:
            statement = statement.where(DailyAnalysisResult.camera_id == camera_id)
        statement = statement.order_by(
            DailyAnalysisResult.camera_id, DailyAnalysisResult.taxonomy_id
        ).execution_options(populate_existing=True)
        return list(session.scalars(statement).all())

    def pending_days(
        self, session: Session, before: date, tz: str | ZoneInfo | None = None
    ) -> list[date]:
        """Return the days before `before` (in tz, defaults to ANALYSIS_TZ)
        that have images not aggregated yet, oldest first."""

        zone = _zone(tz)
        start, _ = day_bounds(before, zone)
        local_day = func.date(func.timezone(zone.key, ImageCapture.captured_at))
        statement = (
            select(local_day)
            .where(
                ImageCapture.tobe_deleted.is_(False),
                ImageCapture.captured_at < start,
            )
            .distinct()
            .order_by(local_day)
        )
        return list(session.scalars(statement).all())

    def recompute_for_image(
        self,
        session: Session,
        image_capture_id: int,
        tz: str | ZoneInfo | None = None,
    ) -> None:
        """Rebuild the results of an image's camera and day (in tz, defaults to
        ANALYSIS_TZ) if the image was already aggregated, e.g. after a user
        correction. Does not commit."""

        image = session.get(ImageCapture, image_capture_id)
        if image is None:
            return

        zone = _zone(tz)
        day = image.captured_at.astimezone(zone).date()
        # wait for a running aggregation of the day, then check if it used the image
        _lock_day(session, day)
        session.refresh(image)
        if image.tobe_deleted:
            self.compute_daily_results(
                session,
                day,
                zone,
                camera_id=image.camera_id,
                recompute=True,
                commit=False,
            )

    def commit_with_recompute(
        self, session: Session, image_capture_id: int | None
    ) -> None:
        """Commit pending changes (e.g. a correction) together with the rebuilt
        results of the image's camera and day. Roll back both on error."""

        try:
            session.flush()
            if image_capture_id is not None:
                self.recompute_for_image(session, image_capture_id)
            session.commit()
        except Exception:
            session.rollback()
            raise


# create an instance of the DailyAnalysisResultCRUD class to be used in other modules
daily_analysis_result_crud = DailyAnalysisResultCRUD()
