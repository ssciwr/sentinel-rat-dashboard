from datetime import timedelta

import pytest

from dashboard.db import (
    daily_analysis_result_crud,
    image_crud,
)
from dashboard.db.analysis_result import (
    DeletedImagesError,
)

from .helpers import (
    DAY,
    TZ,
    add_detection,
    add_image,
    at,
    compute,
    daily_results,
    row_thresholds,
)

NEXT_DAY = DAY + timedelta(days=1)


def _recompute_all(session, before=NEXT_DAY, **kwargs):
    return daily_analysis_result_crud.recompute_all(session, before, TZ, **kwargs)


def test_recompute_all_rebuilds_every_past_camera_and_day(get_session, setup):
    day1 = add_image(get_session, setup, at(0, 30))  # another date in UTC
    add_detection(get_session, setup, day1, [(setup.rat, 0.7)])
    day1_camera2 = add_image(get_session, setup, at(10), camera=setup.camera2)
    add_detection(get_session, setup, day1_camera2, [(setup.mouse, 0.4)])
    day2 = add_image(get_session, setup, at(10, day=NEXT_DAY))
    add_detection(get_session, setup, day2, [(setup.rat, 0.4)])
    for day in (DAY, NEXT_DAY):
        compute(get_session, day=day, clas_threshold=0.5)

    result = _recompute_all(
        get_session, before=NEXT_DAY + timedelta(days=1), clas_threshold=0.3
    )

    assert result.recomputed == [
        (DAY, setup.camera1.id),
        (DAY, setup.camera2.id),
        (NEXT_DAY, setup.camera1.id),
    ]
    assert result.skipped == []
    assert row_thresholds(get_session) == {
        (setup.camera1.id, setup.rat.id): (0.0, 0.3),
        (setup.camera2.id, setup.mouse.id): (0.0, 0.3),
    }
    assert row_thresholds(get_session, day=NEXT_DAY) == {
        (setup.camera1.id, setup.rat.id): (0.0, 0.3)
    }


def test_recompute_all_leaves_days_from_before_on(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])

    result = _recompute_all(get_session, before=DAY)

    assert result == ([], [])
    assert daily_results(get_session) == {}
    get_session.refresh(image)
    assert image.analyzed_at is None


def test_recompute_all_uses_thresholds_of_the_environment(
    get_session, setup, monkeypatch
):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)

    monkeypatch.setenv("DET_CONF_THRESHOLD", "0.2")
    monkeypatch.setenv("CLAS_CONF_THRESHOLD", "0.3")
    _recompute_all(get_session)

    assert row_thresholds(get_session) == {(setup.camera1.id, setup.rat.id): (0.2, 0.3)}


def test_recompute_all_includes_moved_images(get_session, setup):
    moved = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, moved, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)
    image_crud.mark_image_as_moved(get_session, moved.id)

    result = _recompute_all(get_session, clas_threshold=0.3)

    assert result == ([(DAY, setup.camera1.id)], [])
    assert row_thresholds(get_session) == {(setup.camera1.id, setup.rat.id): (0.0, 0.3)}


def test_recompute_all_skips_camera_and_day_with_deleted_image(get_session, setup):
    deleted = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, deleted, [(setup.rat, 0.7)])
    kept = add_image(get_session, setup, at(11))
    add_detection(get_session, setup, kept, [(setup.rat, 0.7)])
    other_camera = add_image(get_session, setup, at(10), camera=setup.camera2)
    add_detection(get_session, setup, other_camera, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)
    image_crud.delete(get_session, deleted.id)

    result = _recompute_all(get_session, clas_threshold=0.9)

    assert result.recomputed == [(DAY, setup.camera2.id)]
    assert result.skipped == [(DAY, setup.camera1.id)]
    # the skipped rows keep their counts and thresholds, the others are rebuilt
    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (2, 0.7)
    }
    assert row_thresholds(get_session) == {(setup.camera1.id, setup.rat.id): (0.0, 0.5)}


def test_recompute_all_skips_results_without_images(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)
    image_crud.delete(get_session, image.id)

    result = _recompute_all(get_session, clas_threshold=0.9)

    assert result == ([], [(DAY, setup.camera1.id)])
    assert row_thresholds(get_session) == {(setup.camera1.id, setup.rat.id): (0.0, 0.5)}


def test_recompute_all_brings_back_results_of_lower_thresholds(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.9)  # everything is filtered
    assert daily_results(get_session) == {}

    _recompute_all(get_session, clas_threshold=0.5)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.7)
    }


def test_recompute_all_includes_missing_and_not_yet_analyzed_images(get_session, setup):
    missing = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, missing, [(setup.rat, 0.7)])
    compute(get_session)
    image_crud.mark_image_as_missing(get_session, missing.id)
    pending = add_image(get_session, setup, at(11))
    add_detection(get_session, setup, pending, [(setup.rat, 0.7)])

    result = _recompute_all(get_session)

    assert result.recomputed == [(DAY, setup.camera1.id)]
    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (2, 0.7)
    }
    get_session.refresh(pending)
    assert pending.analyzed_at is not None


@pytest.mark.parametrize("parameter", ["det_threshold", "clas_threshold"])
def test_recompute_all_refuses_invalid_threshold_before_any_change(
    get_session, setup, parameter
):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)

    with pytest.raises(ValueError, match=parameter):
        _recompute_all(get_session, **{parameter: 1.5})

    assert row_thresholds(get_session) == {(setup.camera1.id, setup.rat.id): (0.0, 0.5)}


def test_recompute_all_skips_camera_and_day_deleted_in_the_meantime(
    get_session, setup, monkeypatch
):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    other_camera = add_image(get_session, setup, at(10), camera=setup.camera2)
    add_detection(get_session, setup, other_camera, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)

    original_compute = daily_analysis_result_crud.compute_daily_results

    def deleted_for_camera1(session, day, tz, *, camera_id, **kwargs):
        if camera_id == setup.camera1.id:
            raise DeletedImagesError(day, camera_id, 2, 1)
        return original_compute(session, day, tz, camera_id=camera_id, **kwargs)

    monkeypatch.setattr(
        daily_analysis_result_crud, "compute_daily_results", deleted_for_camera1
    )

    result = _recompute_all(get_session, clas_threshold=0.3)

    assert result.recomputed == [(DAY, setup.camera2.id)]
    assert result.skipped == [(DAY, setup.camera1.id)]
