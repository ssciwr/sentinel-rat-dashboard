import threading
from datetime import UTC, date, datetime, time, timedelta
from itertools import count
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from dashboard.db import (
    app_user_crud,
    camera_crud,
    classification_correction_crud,
    classification_crud,
    daily_analysis_result_crud,
    detection_correction_crud,
    detection_crud,
    image_crud,
    ml_model_crud,
    taxonomy_crud,
)
from dashboard.db.analysis_result import day_bounds
from dashboard.db.data_model import ClassificationCorrection

TZ = "Asia/Colombo"
DAY = date(2026, 10, 1)
BBOX = {"x": 10, "y": 10, "width": 20, "height": 20}

_image_number = count()


def _at(hour: int, minute: int = 0, day: date = DAY) -> datetime:
    """Local time in TZ on a day."""
    return datetime.combine(day, time(hour, minute), tzinfo=ZoneInfo(TZ))


@pytest.fixture
def setup(get_session):
    session = get_session
    return SimpleNamespace(
        camera1=camera_crud.add(session, name="CAM01", location=(80.6, 7.3)),
        camera2=camera_crud.add(session, name="CAM02", location=(80.7, 7.4)),
        det_model=ml_model_crud.add(session, name="megadetector", task="detection"),
        det_model2=ml_model_crud.add(session, name="yolo", task="detection"),
        clas_model=ml_model_crud.add(session, name="rodent", task="classification"),
        clas_model2=ml_model_crud.add(session, name="other", task="classification"),
        rat=taxonomy_crud.add(session, genus="Rattus", species="rattus"),
        mouse=taxonomy_crud.add(session, genus="Mus", species="musculus"),
        user1=app_user_crud.add(session, username="user1"),
        user2=app_user_crud.add(session, username="user2"),
    )


def _image(session, setup, captured_at, camera=None, **kwargs):
    camera = camera or setup.camera1
    return image_crud.add(
        session,
        camera_id=camera.id,
        image_path=f"{camera.name}_image_{next(_image_number)}.jpg",
        location=(80.6, 7.3),
        captured_at=captured_at,
        **kwargs,
    )


def _detection(session, setup, image, classifications=(), det_model=None):
    """Add a detection with (taxonomy, confidence[, model]) classifications."""
    detection = detection_crud.add(
        session,
        image_capture_id=image.id,
        det_model_id=(det_model or setup.det_model).id,
        confidence=0.9,
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


def _detection_correction(session, setup, image, detection=None, **kwargs):
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


def _classification_correction(session, setup, taxonomy, detection, **kwargs):
    defaults = {
        "species_classification_id": detection.species_classifications[0].id,
        "new_obj_det_id": None,
        "app_user_id": setup.user1.id,
        "corrected_taxonomy_id": taxonomy.id,
        "action": "update",
    }
    return classification_correction_crud.add(session, **(defaults | kwargs))


def _results(session, day=DAY):
    """{(camera_id, taxonomy_id): (count, avg_confidence)} of a day."""
    start, _ = day_bounds(day, TZ)
    return {
        (row.camera_id, row.taxonomy_id): (
            row.taxonomy_count,
            pytest.approx(row.avg_confidence),
        )
        for row in daily_analysis_result_crud.filter(session, start_time=start)
    }


def _compute(session, day=DAY, **kwargs):
    return daily_analysis_result_crud.compute_daily_results(session, day, TZ, **kwargs)


def test_day_bounds_use_timezone():
    start, end = day_bounds(DAY, TZ)

    assert start == datetime(2026, 9, 30, 18, 30, tzinfo=UTC)
    assert end - start == timedelta(days=1)


def test_compute_counts_top_classification_per_camera_and_taxonomy(get_session, setup):
    image1 = _image(get_session, setup, _at(10))
    _detection(get_session, setup, image1, [(setup.rat, 0.9), (setup.mouse, 0.1)])
    _detection(get_session, setup, image1, [(setup.rat, 0.7)])
    _detection(get_session, setup, image1)  # not classified, not counted
    image2 = _image(get_session, setup, _at(11), camera=setup.camera2)
    _detection(get_session, setup, image2, [(setup.mouse, 0.8)])

    rows = _compute(get_session)

    assert _results(get_session) == {
        (setup.camera1.id, setup.rat.id): (2, 0.8),
        (setup.camera2.id, setup.mouse.id): (1, 0.8),
    }
    start, end = day_bounds(DAY, TZ)
    assert all(row.start_time == start and row.end_time == end for row in rows)
    assert len(rows) == 2
    assert image_crud.get_images_to_delete(get_session) == [image1, image2]


def test_compute_uses_only_images_of_the_local_day(get_session, setup):
    inside = [_at(0, 0), _at(23, 59)]
    outside = [_at(23, 59, DAY - timedelta(days=1)), _at(0, 0, DAY + timedelta(days=1))]
    for captured_at in inside + outside:
        image = _image(get_session, setup, captured_at)
        _detection(get_session, setup, image, [(setup.rat, 0.5)])

    _compute(get_session)

    assert _results(get_session) == {(setup.camera1.id, setup.rat.id): (2, 0.5)}
    assert len(image_crud.get_images_to_delete(get_session)) == 2


def test_compute_takes_most_confident_classification_across_models(get_session, setup):
    image = _image(get_session, setup, _at(10))
    _detection(
        get_session,
        setup,
        image,
        [(setup.rat, 0.6, setup.clas_model), (setup.mouse, 0.7, setup.clas_model2)],
    )

    _compute(get_session)

    assert _results(get_session) == {(setup.camera1.id, setup.mouse.id): (1, 0.7)}


def test_compute_refuses_several_detection_models(get_session, setup):
    image = _image(get_session, setup, _at(10))
    _detection(get_session, setup, image, [(setup.rat, 0.6)])
    _detection(get_session, setup, image, [(setup.rat, 0.6)], setup.det_model2)

    with pytest.raises(ValueError, match="several detection models"):
        _compute(get_session)

    assert _results(get_session) == {}
    assert image_crud.get_images_to_delete(get_session) == []


def test_compute_merges_late_images_into_existing_rows(get_session, setup):
    image = _image(get_session, setup, _at(10))
    _detection(get_session, setup, image, [(setup.rat, 0.9)])
    _compute(get_session)

    late_image = _image(get_session, setup, _at(23))
    _detection(get_session, setup, late_image, [(setup.rat, 0.5)])
    _detection(get_session, setup, late_image, [(setup.mouse, 0.4)])
    _compute(get_session)
    # nothing left to aggregate, so running again changes nothing
    _compute(get_session)

    assert _results(get_session) == {
        (setup.camera1.id, setup.rat.id): (2, 0.7),
        (setup.camera1.id, setup.mouse.id): (1, 0.4),
    }


def test_compute_without_images_writes_nothing(get_session, setup):
    assert _compute(get_session) == []
    assert _compute(get_session, recompute=True) == []


def test_compute_applies_latest_detection_correction(get_session, setup):
    image = _image(get_session, setup, _at(10))
    removed = _detection(get_session, setup, image, [(setup.rat, 0.9)])
    kept = _detection(get_session, setup, image, [(setup.rat, 0.5)])
    _detection_correction(get_session, setup, image, removed, action="remove")
    # user1 removed `kept` first, then user2 confirmed it
    _detection_correction(
        get_session,
        setup,
        image,
        kept,
        action="remove",
        last_updated=datetime(2026, 10, 2, tzinfo=UTC),
    )
    _detection_correction(
        get_session,
        setup,
        image,
        kept,
        app_user_id=setup.user2.id,
        last_updated=datetime(2026, 10, 3, tzinfo=UTC),
    )

    _compute(get_session)

    assert _results(get_session) == {(setup.camera1.id, setup.rat.id): (1, 0.5)}


def test_compute_applies_latest_classification_correction(get_session, setup):
    image = _image(get_session, setup, _at(10))
    detection = _detection(get_session, setup, image, [(setup.rat, 0.9)])
    _classification_correction(
        get_session,
        setup,
        setup.rat,
        detection,
        last_updated=datetime(2026, 10, 2, tzinfo=UTC),
    )
    _classification_correction(
        get_session,
        setup,
        setup.mouse,
        detection,
        app_user_id=setup.user2.id,
        last_updated=datetime(2026, 10, 3, tzinfo=UTC),
    )

    _compute(get_session)

    # a species set by a user counts with full confidence
    assert _results(get_session) == {(setup.camera1.id, setup.mouse.id): (1, 1.0)}


def test_compute_counts_detections_added_by_users(get_session, setup):
    image = _image(get_session, setup, _at(10))
    added = _detection_correction(get_session, setup, image)
    _detection_correction(get_session, setup, image)  # no species, not counted
    classification_correction_crud.add(
        get_session,
        species_classification_id=None,
        new_obj_det_id=added.new_detection_id,
        app_user_id=setup.user1.id,
        corrected_taxonomy_id=setup.rat.id,
        action="add",
    )

    _compute(get_session)

    assert _results(get_session) == {(setup.camera1.id, setup.rat.id): (1, 1.0)}


def test_recompute_rebuilds_day_and_drops_stale_rows(get_session, setup):
    image = _image(get_session, setup, _at(10))
    detection = _detection(get_session, setup, image, [(setup.rat, 0.6)])
    _compute(get_session)
    # a new, more confident classification doesn't trigger a recompute by itself
    classification_crud.add(
        get_session,
        object_detection_id=detection.id,
        taxonomy_id=setup.mouse.id,
        clas_model_id=setup.clas_model2.id,
        confidence=0.8,
    )

    _compute(get_session)
    assert _results(get_session) == {(setup.camera1.id, setup.rat.id): (1, 0.6)}

    _compute(get_session, recompute=True)
    assert _results(get_session) == {(setup.camera1.id, setup.mouse.id): (1, 0.8)}


def test_recompute_refused_when_an_image_was_moved(get_session, setup):
    image = _image(get_session, setup, _at(10))
    _detection(get_session, setup, image, [(setup.rat, 0.6)])
    _compute(get_session)
    image_crud.mark_image_as_moved(get_session, image.id)

    with pytest.raises(ValueError, match="moved"):
        _compute(get_session, recompute=True)

    assert _results(get_session) == {(setup.camera1.id, setup.rat.id): (1, 0.6)}


def test_recompute_refused_when_images_are_gone(get_session, setup):
    image = _image(get_session, setup, _at(10))
    _detection(get_session, setup, image, [(setup.rat, 0.6)])
    _compute(get_session)
    image_crud.delete(get_session, image.id)

    with pytest.raises(ValueError, match="gone"):
        _compute(get_session, recompute=True)

    assert _results(get_session) == {(setup.camera1.id, setup.rat.id): (1, 0.6)}


def test_correction_after_aggregation_recomputes_its_camera_and_day(get_session, setup):
    image = _image(get_session, setup, _at(10))
    detection = _detection(get_session, setup, image, [(setup.rat, 0.6)])
    other_image = _image(get_session, setup, _at(10), camera=setup.camera2)
    _detection(get_session, setup, other_image, [(setup.rat, 0.5)])
    _compute(get_session)

    correction = _classification_correction(get_session, setup, setup.mouse, detection)

    assert _results(get_session) == {
        (setup.camera1.id, setup.mouse.id): (1, 1.0),
        (setup.camera2.id, setup.rat.id): (1, 0.5),
    }

    classification_correction_crud.update(
        get_session, correction.id, corrected_taxonomy_id=setup.rat.id
    )

    assert _results(get_session)[(setup.camera1.id, setup.rat.id)] == (1, 1.0)

    classification_correction_crud.delete(get_session, correction.id)

    assert _results(get_session) == {
        (setup.camera1.id, setup.rat.id): (1, 0.6),
        (setup.camera2.id, setup.rat.id): (1, 0.5),
    }

    detection_correction = _detection_correction(get_session, setup, image, detection)
    detection_correction_crud.update(
        get_session, detection_correction.id, action="remove"
    )

    assert _results(get_session) == {(setup.camera2.id, setup.rat.id): (1, 0.5)}

    detection_correction_crud.delete(get_session, detection_correction.id)

    assert _results(get_session)[(setup.camera1.id, setup.rat.id)] == (1, 0.6)


def test_correction_before_aggregation_does_not_aggregate(get_session, setup):
    image = _image(get_session, setup, _at(10))
    detection = _detection(get_session, setup, image, [(setup.rat, 0.6)])

    _classification_correction(get_session, setup, setup.mouse, detection)

    assert _results(get_session) == {}
    assert image_crud.get_images_to_delete(get_session) == []


def test_correction_is_rolled_back_when_recompute_fails(get_session, setup):
    image = _image(get_session, setup, _at(10))
    detection = _detection(get_session, setup, image, [(setup.rat, 0.6)])
    moved_image = _image(get_session, setup, _at(11))
    _compute(get_session)
    image_crud.mark_image_as_moved(get_session, moved_image.id)

    with pytest.raises(ValueError, match="moved"):
        _classification_correction(get_session, setup, setup.mouse, detection)

    assert get_session.scalars(select(ClassificationCorrection)).all() == []
    assert _results(get_session) == {(setup.camera1.id, setup.rat.id): (1, 0.6)}


def test_pending_days_lists_days_with_images_not_aggregated(get_session, setup):
    yesterday = DAY - timedelta(days=1)
    _image(get_session, setup, _at(10, day=yesterday))
    _image(get_session, setup, _at(0, 10))  # 2026-09-30 in UTC
    _image(
        get_session,
        setup,
        _at(10, day=yesterday - timedelta(days=1)),
        tobe_deleted=True,
    )
    _image(get_session, setup, _at(10, day=DAY + timedelta(days=1)))

    pending = daily_analysis_result_crud.pending_days(
        get_session, before=DAY + timedelta(days=1), tz=TZ
    )

    assert pending == [yesterday, DAY]


def test_aggregations_of_the_same_day_wait_for_each_other(
    get_engine_with_tables, get_session, setup
):
    image = _image(get_session, setup, _at(10))
    _detection(get_session, setup, image, [(setup.rat, 0.6)])
    # the first aggregation holds the lock of the day until it commits
    _compute(get_session, commit=False)

    finished = threading.Event()

    def aggregate_again():
        with Session(get_engine_with_tables) as other_session:
            _compute(other_session)
        finished.set()

    thread = threading.Thread(target=aggregate_again)
    thread.start()
    assert not finished.wait(timeout=1)

    get_session.commit()
    thread.join(timeout=10)

    assert finished.is_set()
    # the second aggregation saw the image as aggregated and didn't count it again
    assert _results(get_session) == {(setup.camera1.id, setup.rat.id): (1, 0.6)}
