"""Helpers to set up images and read results in the tests of the daily analysis."""

from datetime import date, datetime, time
from itertools import count
from zoneinfo import ZoneInfo

import pytest

from dashboard.db import (
    classification_correction_crud,
    classification_crud,
    daily_analysis_result_crud,
    detection_correction_crud,
    detection_crud,
    image_crud,
)
from dashboard.db.analysis_result import day_bounds

TZ = "Asia/Colombo"
DAY = date(2026, 10, 1)
BBOX = {"x": 10, "y": 10, "width": 20, "height": 20}

_image_number = count()


def at(hour: int, minute: int = 0, day: date = DAY) -> datetime:
    """Local time in TZ on a day."""
    return datetime.combine(day, time(hour, minute), tzinfo=ZoneInfo(TZ))


def add_image(session, setup, captured_at, camera=None, **kwargs):
    camera = camera or setup.camera1
    return image_crud.add(
        session,
        camera_id=camera.id,
        image_path=f"{camera.name}_image_{next(_image_number)}.jpg",
        location=(80.6, 7.3),
        captured_at=captured_at,
        **kwargs,
    )


def add_detection(
    session, setup, image, classifications=(), det_model=None, det_confidence=0.9
):
    """Add a detection with (taxonomy, confidence[, model]) classifications."""
    detection = detection_crud.add(
        session,
        image_capture_id=image.id,
        det_model_id=(det_model or setup.det_model).id,
        confidence=det_confidence,
        bbox=BBOX,
        detected_class="animal",
    )
    for taxonomy, confidence, *model in classifications:
        classification_crud.add(
            session,
            object_detection_id=detection.id,
            taxonomy_id=taxonomy.id,
            clas_model_id=(model[0] if model else setup.clas_model).id,
            confidence=confidence,
        )
    return detection


def add_detection_correction(session, setup, image, detection=None, **kwargs):
    defaults = {
        "object_detection_id": detection.id if detection else None,
        "image_capture_id": image.id,
        "det_model_id": setup.det_model.id,
        "app_user_id": setup.user1.id,
        "corrected_bbox": BBOX,
        "corrected_class": "animal",
        "action": "update" if detection else "add",
    }
    return detection_correction_crud.add(session, **(defaults | kwargs))


def add_classification_correction(session, setup, taxonomy, detection, **kwargs):
    defaults = {
        "species_classification_id": detection.species_classifications[0].id,
        "new_obj_det_id": None,
        "app_user_id": setup.user1.id,
        "corrected_taxonomy_id": taxonomy.id,
        "action": "update",
    }
    return classification_correction_crud.add(session, **(defaults | kwargs))


def daily_results(session, day=DAY):
    """{(camera_id, det_model_id, taxonomy_id): (count, avg_confidence)} of a day."""
    start, _ = day_bounds(day, TZ)
    return {
        (row.camera_id, row.det_model_id, row.taxonomy_id): (
            row.taxonomy_count,
            pytest.approx(row.avg_confidence),
        )
        for row in daily_analysis_result_crud.filter(session, start_time=start)
    }


def compute(session, day=DAY, **kwargs):
    return daily_analysis_result_crud.compute_daily_results(session, day, TZ, **kwargs)


def row_thresholds(session, day=DAY):
    """{(camera_id, taxonomy_id): (det_threshold, clas_threshold)} of a day."""
    start, _ = day_bounds(day, TZ)
    return {
        (row.camera_id, row.taxonomy_id): (row.det_threshold, row.clas_threshold)
        for row in daily_analysis_result_crud.filter(session, start_time=start)
    }
