import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from dashboard.db import (
    classification_correction_crud,
    daily_analysis_result_crud,
    image_crud,
)
from dashboard.db.analysis_result import (
    day_bounds,
)

from .helpers import (
    DAY,
    TZ,
    add_classification_correction,
    add_detection,
    add_detection_correction,
    add_image,
    at,
    compute,
    daily_results,
)


def test_day_bounds_use_timezone():
    start, end = day_bounds(DAY, TZ)

    assert start == datetime(2026, 9, 30, 18, 30, tzinfo=UTC)
    assert end - start == timedelta(days=1)


def test_compute_counts_top_classification_per_camera_and_taxonomy(get_session, setup):
    image1 = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image1, [(setup.rat, 0.9), (setup.mouse, 0.1)])
    add_detection(get_session, setup, image1, [(setup.rat, 0.7)])
    add_detection(get_session, setup, image1)  # not classified, not counted
    image2 = add_image(get_session, setup, at(11), camera=setup.camera2)
    add_detection(get_session, setup, image2, [(setup.mouse, 0.8)])

    rows = compute(get_session)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (2, 0.8),
        (setup.camera2.id, setup.det_model.id, setup.mouse.id): (1, 0.8),
    }
    start, end = day_bounds(DAY, TZ)
    assert all(row.start_time == start and row.end_time == end for row in rows)
    assert len(rows) == 2
    assert image_crud.get_images_to_move(get_session) == [image1, image2]


def test_compute_uses_only_images_of_the_local_day(get_session, setup):
    inside = [at(0, 0), at(23, 59)]
    outside = [at(23, 59, DAY - timedelta(days=1)), at(0, 0, DAY + timedelta(days=1))]
    for captured_at in inside + outside:
        image = add_image(get_session, setup, captured_at)
        add_detection(get_session, setup, image, [(setup.rat, 0.5)])

    compute(get_session)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (2, 0.5)
    }
    assert len(image_crud.get_images_to_move(get_session)) == 2


def test_compute_takes_most_confident_classification_across_models(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(
        get_session,
        setup,
        image,
        [(setup.rat, 0.6, setup.clas_model), (setup.mouse, 0.7, setup.clas_model2)],
    )

    compute(get_session)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.mouse.id): (1, 0.7)
    }


def test_compute_counts_each_detection_model_separately(get_session, setup):
    image = add_image(get_session, setup, at(10))
    # both models detected the same rat
    add_detection(get_session, setup, image, [(setup.rat, 0.6)])
    add_detection(get_session, setup, image, [(setup.rat, 0.8)], setup.det_model2)
    # a user added a detection the second model missed
    added = add_detection_correction(
        get_session, setup, image, det_model_id=setup.det_model2.id
    )
    classification_correction_crud.add(
        get_session,
        species_classification_id=None,
        new_obj_det_id=added.new_detection_id,
        app_user_id=setup.user1.id,
        corrected_taxonomy_id=setup.mouse.id,
        action="add",
    )

    compute(get_session)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.6),
        (setup.camera1.id, setup.det_model2.id, setup.rat.id): (1, 0.8),
        (setup.camera1.id, setup.det_model2.id, setup.mouse.id): (1, 1.0),
    }


def test_compute_merges_late_images_into_existing_rows(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.9)])
    compute(get_session)

    late_image = add_image(get_session, setup, at(23))
    add_detection(get_session, setup, late_image, [(setup.rat, 0.5)])
    add_detection(get_session, setup, late_image, [(setup.mouse, 0.4)])
    compute(get_session)
    # nothing left to aggregate, so running again changes nothing
    compute(get_session)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (2, 0.7),
        (setup.camera1.id, setup.det_model.id, setup.mouse.id): (1, 0.4),
    }


def test_compute_without_images_writes_nothing(get_session, setup):
    assert compute(get_session) == []
    assert compute(get_session, recompute=True) == []


def test_compute_applies_latest_detection_correction(get_session, setup):
    image = add_image(get_session, setup, at(10))
    removed = add_detection(get_session, setup, image, [(setup.rat, 0.9)])
    kept = add_detection(get_session, setup, image, [(setup.rat, 0.5)])
    add_detection_correction(get_session, setup, image, removed, action="remove")
    # user1 removed `kept` first, then user2 confirmed it
    add_detection_correction(
        get_session,
        setup,
        image,
        kept,
        action="remove",
        last_updated=datetime(2026, 10, 2, tzinfo=UTC),
    )
    add_detection_correction(
        get_session,
        setup,
        image,
        kept,
        app_user_id=setup.user2.id,
        last_updated=datetime(2026, 10, 3, tzinfo=UTC),
    )

    compute(get_session)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.5)
    }


def test_compute_applies_latest_classification_correction(get_session, setup):
    image = add_image(get_session, setup, at(10))
    detection = add_detection(get_session, setup, image, [(setup.rat, 0.9)])
    add_classification_correction(
        get_session,
        setup,
        setup.rat,
        detection,
        last_updated=datetime(2026, 10, 2, tzinfo=UTC),
    )
    add_classification_correction(
        get_session,
        setup,
        setup.mouse,
        detection,
        app_user_id=setup.user2.id,
        last_updated=datetime(2026, 10, 3, tzinfo=UTC),
    )

    compute(get_session)

    # a species set by a user counts with full confidence
    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.mouse.id): (1, 1.0)
    }


def test_compute_counts_detections_added_by_users(get_session, setup):
    image = add_image(get_session, setup, at(10))
    added = add_detection_correction(get_session, setup, image)
    add_detection_correction(get_session, setup, image)  # no species, not counted
    classification_correction_crud.add(
        get_session,
        species_classification_id=None,
        new_obj_det_id=added.new_detection_id,
        app_user_id=setup.user1.id,
        corrected_taxonomy_id=setup.rat.id,
        action="add",
    )

    compute(get_session)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 1.0)
    }


def test_pending_days_lists_days_with_images_not_aggregated(get_session, setup):
    yesterday = DAY - timedelta(days=1)
    add_image(get_session, setup, at(10, day=yesterday))
    add_image(get_session, setup, at(0, 10))  # 2026-09-30 in UTC
    analyzed = add_image(get_session, setup, at(10, day=yesterday - timedelta(days=1)))
    image_crud.mark_image_as_analyzed(get_session, analyzed.id)
    add_image(get_session, setup, at(10, day=DAY + timedelta(days=1)))

    pending = daily_analysis_result_crud.pending_days(
        get_session, before=DAY + timedelta(days=1), tz=TZ
    )

    assert pending == [yesterday, DAY]


def test_aggregations_of_the_same_day_wait_for_each_other(
    get_engine_with_tables, get_session, setup
):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.6)])
    # the first aggregation holds the lock of the day until it commits
    compute(get_session, commit=False)

    finished = threading.Event()

    def aggregate_again():
        with Session(get_engine_with_tables) as other_session:
            compute(other_session)
        finished.set()

    thread = threading.Thread(target=aggregate_again)
    thread.start()
    assert not finished.wait(timeout=1)

    get_session.commit()
    thread.join(timeout=10)

    assert finished.is_set()
    # the second aggregation saw the image as aggregated and didn't count it again
    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.6)
    }
