"""CRUD helpers for the daily_analysis_result table"""

import os
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import NamedTuple
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

# environment variables with the global confidence thresholds of all models
DET_CONF_THRESHOLD_ENV = "DET_CONF_THRESHOLD"
CLAS_CONF_THRESHOLD_ENV = "CLAS_CONF_THRESHOLD"

# threshold if none is given, keeps all results
NO_THRESHOLD = 0.0


class DeletedImagesError(ValueError):
    """A camera and day can't be rebuilt, since some of its images were deleted
    and their results would be lost."""

    def __init__(self, day: date, camera_id: int, expected: int, found: int):
        super().__init__(
            f"Cannot recompute {day} of camera {camera_id}: {expected - found} of its "
            f"{expected} analyzed image(s) are gone, and their results would be lost."
        )
        self.day = day
        self.camera_id = camera_id


@dataclass(frozen=True)
class CorrectionDeleteResult:
    """Result of deleting a correction. It is true if the correction was deleted.
    daily_analysis_warning is a message for the user, or None if there is nothing
    to tell, like the attribute of the same name of a correction that was saved."""

    deleted: bool
    daily_analysis_warning: str | None = None

    def __bool__(self) -> bool:
        return self.deleted


class RecomputeAllResult(NamedTuple):
    """The (day, camera_id) pairs that recompute_all rebuilt or left as they were."""

    recomputed: list[tuple[date, int]]
    skipped: list[tuple[date, int]]


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


def _checked_threshold(name: str, threshold: float) -> float:
    if not 0 <= threshold <= 1:
        raise ValueError(f"{name} must be between 0 and 1, got {threshold!r}")
    return threshold


def _env_threshold(name: str) -> float:
    """Return the threshold in an environment variable, NO_THRESHOLD if it is not set
    or empty."""

    value = os.getenv(name, "").strip()
    if not value:
        return NO_THRESHOLD
    try:
        threshold = float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc
    return _checked_threshold(name, threshold)


def _resolve_thresholds(
    det_threshold: float | None, clas_threshold: float | None
) -> tuple[float, float]:
    """Return the (detection, classification) thresholds to use: the given ones,
    else the ones in the environment variables, else NO_THRESHOLD.
    Raises ValueError if a threshold used is not a number between 0 and 1."""

    return (
        (
            _env_threshold(DET_CONF_THRESHOLD_ENV)
            if det_threshold is None
            else _checked_threshold("det_threshold", det_threshold)
        ),
        (
            _env_threshold(CLAS_CONF_THRESHOLD_ENV)
            if clas_threshold is None
            else _checked_threshold("clas_threshold", clas_threshold)
        ),
    )


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


def _detection_species(
    detection: ObjectDetection, det_threshold: float, clas_threshold: float
) -> tuple[int, float] | None:
    """Return (taxonomy_id, confidence) of a model detection after user corrections,
    or None if the detection was removed, has no species or is below a threshold.

    Thresholds only filter model results, and a result at a threshold is kept.
    A species set by a user always counts, and a detection confirmed by a user
    skips det_threshold, but its classifications still have to meet clas_threshold."""

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

    if correction is None and detection.confidence < det_threshold:
        return None

    # the most confident classification wins, also across classification models
    top = max(
        (
            classification
            for classification in detection.species_classifications
            if classification.confidence >= clas_threshold
        ),
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


def _image_species(
    image: ImageCapture, det_threshold: float, clas_threshold: float
) -> list[tuple[int, int, float]]:
    """Return (det_model_id, taxonomy_id, confidence) of every detection in an image
    that has a species after user corrections and confidence thresholds.

    Detections of different detection models can't be matched to each other,
    so each detection model is counted separately."""

    species = [
        (
            detection.det_model_id,
            _detection_species(detection, det_threshold, clas_threshold),
        )
        for detection in image.object_detections
    ]
    # an added detection belongs to the detection model it was added for
    species += [
        (correction.det_model_id, _added_detection_species(correction))
        for correction in image.detection_corrections
        if correction.new_detection_id is not None
    ]
    return [(det_model_id, *item) for det_model_id, item in species if item is not None]


def _refuse_deleted_images(
    day: date,
    existing_rows: list[DailyAnalysisResult],
    analyzed_counts: dict[int, int],
) -> None:
    """Raise DeletedImagesError if a camera has fewer analyzed images than its rows
    were computed from, since rebuilding them would lose the results of the others."""

    for camera, stored_count in _stored_counts(existing_rows).items():
        analyzed_count = analyzed_counts.get(camera, 0)
        if analyzed_count < stored_count:
            raise DeletedImagesError(day, camera, stored_count, analyzed_count)


def _stored_counts(existing_rows: list[DailyAnalysisResult]) -> dict[int, int]:
    return {row.camera_id: row.image_count for row in existing_rows}


def _image_counts(
    images: list[ImageCapture],
    existing_rows: list[DailyAnalysisResult],
    analyzed_counts: dict[int, int],
    recompute: bool,
) -> dict[int, int]:
    """Return the number of analyzed images per camera after this aggregation."""

    stored_counts = _stored_counts(existing_rows)
    new_counts = Counter(
        image.camera_id for image in images if image.analyzed_at is None
    )

    image_counts = {}
    for camera in {*stored_counts, *analyzed_counts, *new_counts}:
        if recompute:
            # a rebuild recounts everything, deletions were refused before
            already_counted = analyzed_counts.get(camera, 0)
        elif camera in stored_counts:
            # keep counting from the stored number, so that deletions stay detectable
            already_counted = stored_counts[camera]
        else:
            # no rows yet, e.g. all earlier results of the camera were filtered out
            already_counted = analyzed_counts.get(camera, 0)
        image_counts[camera] = already_counted + new_counts[camera]
    return image_counts


def _species_totals(
    images: list[ImageCapture],
    thresholds_of_camera: Callable[[int], tuple[float, float]],
) -> dict[tuple[int, int, int], list[float]]:
    """Return [count, sum of confidences] of the species in the images,
    per (camera_id, det_model_id, taxonomy_id)."""

    totals: defaultdict[tuple[int, int, int], list[float]] = defaultdict(
        lambda: [0, 0.0]
    )
    for image in images:
        for det_model_id, taxonomy_id, confidence in _image_species(
            image, *thresholds_of_camera(image.camera_id)
        ):
            total = totals[(image.camera_id, det_model_id, taxonomy_id)]
            total[0] += 1
            total[1] += confidence
    return totals


def _merge_into_row(
    row: DailyAnalysisResult, count: int, confidence_sum: float
) -> None:
    """Add the counts of late images to an existing row."""

    merged_count = row.taxonomy_count + count
    row.avg_confidence = (
        row.avg_confidence * row.taxonomy_count + confidence_sum
    ) / merged_count
    row.taxonomy_count = merged_count


def _mark_as_analyzed(images: list[ImageCapture]) -> None:
    """Set analyzed_at, keeping the time an image was first analyzed if it is
    recomputed."""

    analyzed_at = datetime.now(UTC)
    for image in images:
        if image.analyzed_at is None:
            image.analyzed_at = analyzed_at


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
        keep_thresholds: bool = False,
        commit: bool = True,
        det_threshold: float | None = None,
        clas_threshold: float | None = None,
    ) -> list[DailyAnalysisResult]:
        """Aggregate the detections of the images captured on a day into
        daily_analysis_result, one row per camera, detection model and taxonomy,
        and mark the images as analyzed (set analyzed_at).

        The day runs from midnight to midnight in tz (defaults to ANALYSIS_TZ).
        User corrections override the model results; per item, the latest one wins.

        Model results below a confidence threshold are left out, and each row stores
        the thresholds it was computed with.

        By default, only images not aggregated yet (analyzed_at is NULL) are used,
        and their counts are merged into the existing rows of the day. Images of a
        camera that already has rows of the day use the thresholds of those rows,
        so that the thresholds stored in a row stay true for all of its counts.
        With recompute=True, all images of the day are used and the rows of the day
        are rebuilt with the thresholds of this call, also from images moved out of the
        watch folder, as their results stay in the database. Raises DeletedImagesError
        if some analyzed images were deleted, since their results would be lost.
        With keep_thresholds=True as well, a camera that has rows of the day keeps
        the thresholds of those rows, e.g. when a user correction rebuilds them.

        With commit=False, the changes are only flushed, so the caller can commit
        them together with other changes (e.g. the correction that caused them).

        det_threshold and clas_threshold default to the environment variables
        DET_CONF_THRESHOLD and CLAS_CONF_THRESHOLD, and then to 0.0. A threshold that
        is not a number between 0 and 1 raises ValueError, and nothing is changed.

        Returns the rows of the day (of camera_id, if given).
        """

        thresholds = _resolve_thresholds(det_threshold, clas_threshold)

        start, end = day_bounds(day, tz)
        try:
            self._aggregate(
                session,
                day,
                start,
                end,
                camera_id,
                recompute,
                keep_thresholds,
                thresholds,
            )
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
        keep_thresholds: bool,
        thresholds: tuple[float, float],
    ) -> None:
        _lock_day(session, day)

        images = self._images_to_aggregate(session, start, end, camera_id, recompute)
        existing_rows = self._day_rows(session, start, camera_id)
        analyzed_counts = self._analyzed_image_counts(session, start, end, camera_id)
        if recompute:
            _refuse_deleted_images(day, existing_rows, analyzed_counts)
        image_counts = _image_counts(images, existing_rows, analyzed_counts, recompute)

        # camera_id -> (det_threshold, clas_threshold) of its rows of the day
        kept_thresholds = (
            {
                row.camera_id: (row.det_threshold, row.clas_threshold)
                for row in existing_rows
            }
            if keep_thresholds or not recompute
            else {}
        )

        def thresholds_of_camera(camera: int) -> tuple[float, float]:
            return kept_thresholds.get(camera, thresholds)

        totals = _species_totals(images, thresholds_of_camera)

        if recompute:
            self._delete_day_rows(session, start, camera_id)
            existing_rows = []
        self._write_rows(
            session,
            start,
            end,
            existing_rows,
            totals,
            image_counts,
            thresholds_of_camera,
        )

        _mark_as_analyzed(images)
        session.flush()

    def _images_to_aggregate(
        self,
        session: Session,
        start: datetime,
        end: datetime,
        camera_id: int | None,
        recompute: bool,
    ) -> list[ImageCapture]:
        """Return the images of a day (of camera_id, if given) with their results and
        corrections: all of them for a recompute, else the ones not aggregated yet."""

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
            statement = statement.where(ImageCapture.analyzed_at.is_(None))
        return list(session.scalars(statement).all())

    def _delete_day_rows(
        self, session: Session, start: datetime, camera_id: int | None
    ) -> None:
        """Delete the rows of a day (of camera_id, if given)."""

        statement = delete(DailyAnalysisResult).where(
            DailyAnalysisResult.start_time == start
        )
        if camera_id is not None:
            statement = statement.where(DailyAnalysisResult.camera_id == camera_id)
        session.execute(statement)

    def _write_rows(
        self,
        session: Session,
        start: datetime,
        end: datetime,
        existing_rows: list[DailyAnalysisResult],
        totals: dict[tuple[int, int, int], list[float]],
        image_counts: dict[int, int],
        thresholds_of_camera: Callable[[int], tuple[float, float]],
    ) -> None:
        """Merge the totals into the existing rows, add rows for the other ones,
        and update the image count of all rows."""

        rows = {
            (row.camera_id, row.det_model_id, row.taxonomy_id): row
            for row in existing_rows
        }
        for key, (count, confidence_sum) in totals.items():
            row = rows.get(key)
            if row is not None:
                _merge_into_row(row, count, confidence_sum)
                continue

            camera, det_model_id, taxonomy_id = key
            det_threshold, clas_threshold = thresholds_of_camera(camera)
            session.add(
                DailyAnalysisResult(
                    camera_id=camera,
                    start_time=start,
                    end_time=end,
                    det_model_id=det_model_id,
                    taxonomy_id=taxonomy_id,
                    taxonomy_count=count,
                    avg_confidence=confidence_sum / count,
                    det_threshold=det_threshold,
                    clas_threshold=clas_threshold,
                    image_count=image_counts[camera],
                )
            )

        for row in existing_rows:
            row.image_count = image_counts[row.camera_id]

    def _analyzed_image_counts(
        self, session: Session, start: datetime, end: datetime, camera_id: int | None
    ) -> dict[int, int]:
        """Return the number of analyzed images of a day per camera (of camera_id,
        if given)."""
        statement = (
            select(ImageCapture.camera_id, func.count())
            .where(
                ImageCapture.captured_at >= start,
                ImageCapture.captured_at < end,
                ImageCapture.analyzed_at.is_not(None),
            )
            .group_by(ImageCapture.camera_id)
        )
        if camera_id is not None:
            statement = statement.where(ImageCapture.camera_id == camera_id)
        return dict(session.execute(statement).all())

    def _day_rows(
        self, session: Session, start: datetime, camera_id: int | None
    ) -> list[DailyAnalysisResult]:
        """Return the rows of a day and camera_id (if given)."""
        statement = select(DailyAnalysisResult).where(
            DailyAnalysisResult.start_time == start
        )
        if camera_id is not None:
            statement = statement.where(DailyAnalysisResult.camera_id == camera_id)
        statement = statement.order_by(
            DailyAnalysisResult.camera_id,
            DailyAnalysisResult.det_model_id,
            DailyAnalysisResult.taxonomy_id,
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
                ImageCapture.analyzed_at.is_(None),
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
        correction, with the thresholds its rows already have, so that a correction
        doesn't change other counts. Does not commit."""

        image = session.get(ImageCapture, image_capture_id)
        if image is None:
            return

        zone = _zone(tz)
        day = image.captured_at.astimezone(zone).date()
        # wait for a running aggregation of the day, then check if it used the image
        _lock_day(session, day)
        session.refresh(image)
        if image.analyzed_at is not None:
            self.compute_daily_results(
                session,
                day,
                zone,
                camera_id=image.camera_id,
                recompute=True,
                keep_thresholds=True,
                commit=False,
            )

    def recompute_all(
        self,
        session: Session,
        before: date,
        tz: str | ZoneInfo | None = None,
        *,
        det_threshold: float | None = None,
        clas_threshold: float | None = None,
    ) -> RecomputeAllResult:
        """Rebuild the results of the days before `before` (in tz, defaults to
        ANALYSIS_TZ) per camera, e.g. after the thresholds changed. Each camera and day
        is committed on its own, so a failure keeps the ones rebuilt so far.

        Images moved out of the watch folder are included. Skipped are a camera and day
        with deleted images, since their results would be lost. They keep their rows,
        with the thresholds stored in them. Thresholds default like in
        compute_daily_results.
        """

        # the same thresholds for all, and refuse invalid ones before changing anything
        det_threshold, clas_threshold = _resolve_thresholds(
            det_threshold, clas_threshold
        )
        zone = _zone(tz)
        start, _ = day_bounds(before, zone)

        local_day = func.date(func.timezone(zone.key, ImageCapture.captured_at))
        with_images = {
            (day, camera_id)
            for day, camera_id in session.execute(
                select(local_day, ImageCapture.camera_id)
                .where(ImageCapture.captured_at < start)
                .distinct()
            )
        }
        with_results = {
            (day, camera_id)
            for day, camera_id in session.execute(
                select(
                    func.date(func.timezone(zone.key, DailyAnalysisResult.start_time)),
                    DailyAnalysisResult.camera_id,
                )
                .where(DailyAnalysisResult.start_time < start)
                .distinct()
            )
        }

        # results without any image left can't be rebuilt either
        skipped = with_results - with_images
        recomputed = []
        for day, camera_id in sorted(with_images):
            try:
                self.compute_daily_results(
                    session,
                    day,
                    zone,
                    camera_id=camera_id,
                    recompute=True,
                    # replace the stored thresholds with the ones of this run
                    keep_thresholds=False,
                    det_threshold=det_threshold,
                    clas_threshold=clas_threshold,
                )
            except DeletedImagesError:
                skipped.add((day, camera_id))
            else:
                recomputed.append((day, camera_id))
        return RecomputeAllResult(recomputed, sorted(skipped))

    def commit_with_recompute(
        self, session: Session, image_capture_id: int | None
    ) -> str | None:
        """Commit pending changes (e.g. a correction) together with the rebuilt
        results of the image's camera and day. Roll back both on error.

        If the results can't be rebuilt since some images were deleted, the changes are
        committed anyway. Returns a warning message for the user in that case,
        otherwise None."""

        message = None
        try:
            session.flush()
            if image_capture_id is not None:
                try:
                    self.recompute_for_image(session, image_capture_id)
                except DeletedImagesError as error:
                    message = (
                        "Your correction is saved, but the daily analysis of "
                        f"{error.day} for camera {error.camera_id} can't be updated, "
                        "because some of its images were deleted."
                    )
            session.commit()
        except Exception:
            session.rollback()
            raise
        return message


# create an instance of the DailyAnalysisResultCRUD class to be used in other modules
daily_analysis_result_crud = DailyAnalysisResultCRUD()
