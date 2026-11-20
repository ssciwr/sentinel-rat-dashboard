import pytest

from dashboard.db import (
    classification_correction_crud,
    daily_analysis_result_crud,
    detection_correction_crud,
    image_crud,
)
from dashboard.db.analysis_result import (
    DeletedImagesError,
    day_bounds,
)
from dashboard.db.data_model import ClassificationCorrection

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


def _row_image_counts(session, day=DAY):
    """{taxonomy_id: image_count} of the rows of a day."""
    start, _ = day_bounds(day, TZ)
    return {
        row.taxonomy_id: row.image_count
        for row in daily_analysis_result_crud.filter(session, start_time=start)
    }


def _day_with_deleted_image(session, setup):
    """Add and aggregate two images, delete one, and return the image left and a
    detection of it."""
    deleted = add_image(session, setup, at(10))
    add_detection(session, setup, deleted, [(setup.rat, 0.7)])
    kept = add_image(session, setup, at(11))
    detection = add_detection(session, setup, kept, [(setup.rat, 0.5)])
    compute(session)
    image_crud.delete(session, deleted.id)
    return kept, detection


def _warning_of_camera1(setup):
    return (
        "Your correction is saved, but the daily analysis of 2026-10-01 for camera "
        f"{setup.camera1.id} can't be updated, because some of its images were deleted."
    )


def test_rows_store_analyzed_images_of_their_camera_and_day(get_session, setup):
    with_rat = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, with_rat, [(setup.rat, 0.7)])
    add_image(get_session, setup, at(11))  # without results, but analyzed
    other_camera = add_image(get_session, setup, at(10), camera=setup.camera2)
    add_detection(get_session, setup, other_camera, [(setup.mouse, 0.7)])

    compute(get_session)

    assert _row_image_counts(get_session) == {setup.rat.id: 2, setup.mouse.id: 1}


def test_late_images_update_image_count_of_all_rows_of_the_camera(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session)

    late = add_image(get_session, setup, at(11))
    add_detection(get_session, setup, late, [(setup.mouse, 0.7)])
    compute(get_session)

    assert _row_image_counts(get_session) == {setup.rat.id: 2, setup.mouse.id: 2}


def test_first_row_counts_images_analyzed_without_results(get_session, setup):
    filtered = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, filtered, [(setup.rat, 0.1)])
    compute(get_session, clas_threshold=0.5)
    assert _row_image_counts(get_session) == {}

    late = add_image(get_session, setup, at(11))
    add_detection(get_session, setup, late, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)

    assert _row_image_counts(get_session) == {setup.rat.id: 2}


def test_recompute_refused_when_some_images_are_deleted(get_session, setup):
    deleted = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, deleted, [(setup.rat, 0.7)])
    kept = add_image(get_session, setup, at(11))
    add_detection(get_session, setup, kept, [(setup.rat, 0.5)])
    compute(get_session)
    image_crud.delete(get_session, deleted.id)

    with pytest.raises(DeletedImagesError, match="1 of its 2"):
        compute(get_session, recompute=True)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (2, 0.6)
    }


def test_day_recompute_refused_when_one_camera_has_deleted_images(get_session, setup):
    deleted = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, deleted, [(setup.rat, 0.7)])
    other_camera = add_image(get_session, setup, at(10), camera=setup.camera2)
    add_detection(get_session, setup, other_camera, [(setup.rat, 0.7)])
    compute(get_session)
    image_crud.delete(get_session, deleted.id)

    with pytest.raises(DeletedImagesError):
        compute(get_session, recompute=True)


@pytest.mark.parametrize("aggregate_late_image", [False, True])
def test_late_image_does_not_hide_deleted_images(
    get_session, setup, aggregate_late_image
):
    deleted = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, deleted, [(setup.rat, 0.7)])
    compute(get_session)
    image_crud.delete(get_session, deleted.id)

    late = add_image(get_session, setup, at(11))
    add_detection(get_session, setup, late, [(setup.rat, 0.7)])
    if aggregate_late_image:
        compute(get_session)

    with pytest.raises(DeletedImagesError):
        compute(get_session, recompute=True)


def test_recompute_updates_image_count(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session)
    pending = add_image(get_session, setup, at(11))
    add_detection(get_session, setup, pending, [(setup.rat, 0.7)])

    compute(get_session, recompute=True)

    assert _row_image_counts(get_session) == {setup.rat.id: 2}


def test_classification_correction_with_deleted_images_returns_warning(
    get_session, setup
):
    _, detection = _day_with_deleted_image(get_session, setup)

    correction = add_classification_correction(
        get_session, setup, setup.mouse, detection
    )

    assert correction.daily_analysis_warning == _warning_of_camera1(setup)
    # the correction is committed, the daily results stay as they were
    get_session.rollback()
    assert get_session.get(ClassificationCorrection, correction.id) is not None
    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (2, 0.6)
    }

    updated = classification_correction_crud.update(
        get_session, correction.id, corrected_taxonomy_id=setup.rat.id
    )
    assert updated.corrected_taxonomy_id == setup.rat.id
    assert updated.daily_analysis_warning == _warning_of_camera1(setup)

    result = classification_correction_crud.delete(get_session, correction.id)
    assert result.deleted is True
    assert result.daily_analysis_warning == _warning_of_camera1(setup)


def test_detection_correction_with_deleted_images_returns_warning(get_session, setup):
    kept, detection = _day_with_deleted_image(get_session, setup)

    correction = add_detection_correction(get_session, setup, kept, detection)
    assert correction.daily_analysis_warning == _warning_of_camera1(setup)

    updated = detection_correction_crud.update(
        get_session, correction.id, action="remove"
    )
    assert updated.action == "remove"
    assert updated.daily_analysis_warning == _warning_of_camera1(setup)

    result = detection_correction_crud.delete(get_session, correction.id)
    assert result.deleted is True
    assert result.daily_analysis_warning == _warning_of_camera1(setup)


def test_correction_without_deleted_images_returns_no_warning(get_session, setup):
    image = add_image(get_session, setup, at(10))
    detection = add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session)

    correction = add_classification_correction(
        get_session, setup, setup.mouse, detection
    )
    assert correction.daily_analysis_warning is None

    updated = classification_correction_crud.update(
        get_session, correction.id, corrected_taxonomy_id=setup.rat.id
    )
    assert updated.daily_analysis_warning is None

    result = classification_correction_crud.delete(get_session, correction.id)
    assert result.deleted is True
    assert result.daily_analysis_warning is None


def test_update_without_changes_clears_the_warning_of_an_earlier_call(
    get_session, setup
):
    _, detection = _day_with_deleted_image(get_session, setup)
    correction = add_classification_correction(
        get_session, setup, setup.mouse, detection
    )
    assert correction.daily_analysis_warning is not None

    updated = classification_correction_crud.update(get_session, correction.id)

    assert updated.daily_analysis_warning is None


@pytest.mark.parametrize(
    "crud", [classification_correction_crud, detection_correction_crud]
)
def test_delete_of_unknown_correction_is_false(get_session, crud):
    result = crud.delete(get_session, -1)

    assert not result
    assert result.deleted is False
    assert result.daily_analysis_warning is None
