import pytest

from dashboard.db import (
    classification_correction_crud,
)

from .helpers import (
    add_classification_correction,
    add_detection,
    add_detection_correction,
    add_image,
    at,
    compute,
    daily_results,
    row_thresholds,
)


def test_compute_filters_detections_below_threshold(get_session, setup):
    image = add_image(get_session, setup, at(10))
    rat = [(setup.rat, 0.9)]
    add_detection(get_session, setup, image, rat, det_confidence=0.49)  # below
    add_detection(get_session, setup, image, rat, det_confidence=0.5)  # at threshold
    add_detection(get_session, setup, image, rat, det_confidence=0.8)  # above

    compute(get_session, det_threshold=0.5)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (2, 0.9)
    }


def test_compute_filters_classifications_below_threshold(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.49)])  # below
    add_detection(get_session, setup, image, [(setup.rat, 0.5)])  # at threshold
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])  # above

    compute(get_session, clas_threshold=0.5)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (2, 0.6)
    }


def test_compute_applies_threshold_to_all_models(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(
        get_session,
        setup,
        image,
        [(setup.rat, 0.4), (setup.mouse, 0.3, setup.clas_model2)],
    )
    add_detection(
        get_session,
        setup,
        image,
        [(setup.mouse, 0.8, setup.clas_model2)],
        det_model=setup.det_model2,
        det_confidence=0.4,
    )

    compute(get_session, det_threshold=0.5, clas_threshold=0.5)

    assert daily_results(get_session) == {}


def test_compute_uses_thresholds_of_the_environment(get_session, setup, monkeypatch):
    monkeypatch.setenv("DET_CONF_THRESHOLD", "0.5")
    monkeypatch.setenv("CLAS_CONF_THRESHOLD", "0.6")
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)], det_confidence=0.4)
    add_detection(get_session, setup, image, [(setup.rat, 0.5)], det_confidence=0.6)
    add_detection(get_session, setup, image, [(setup.mouse, 0.7)], det_confidence=0.6)

    compute(get_session)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.mouse.id): (1, 0.7)
    }
    assert row_thresholds(get_session) == {
        (setup.camera1.id, setup.mouse.id): (0.5, 0.6)
    }


def test_compute_marks_image_analyzed_when_all_results_are_filtered(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])

    assert compute(get_session, clas_threshold=0.8) == []

    get_session.refresh(image)
    assert image.analyzed_at is not None


def test_thresholds_do_not_filter_user_corrections(get_session, setup):
    image = add_image(get_session, setup, at(10))
    # the user set the species of a detection below both thresholds
    reclassified = add_detection(
        get_session, setup, image, [(setup.rat, 0.1)], det_confidence=0.1
    )
    add_classification_correction(get_session, setup, setup.mouse, reclassified)
    # the user confirmed a detection below the threshold, its classification passes
    confirmed = add_detection(
        get_session, setup, image, [(setup.rat, 0.9)], det_confidence=0.1
    )
    add_detection_correction(get_session, setup, image, confirmed)
    # a confirmed detection doesn't lift the threshold of its classification
    unclassified = add_detection(
        get_session, setup, image, [(setup.rat, 0.1)], det_confidence=0.1
    )
    add_detection_correction(get_session, setup, image, unclassified)
    # a detection added by a user has no confidence to filter
    added = add_detection_correction(get_session, setup, image)
    classification_correction_crud.add(
        get_session,
        species_classification_id=None,
        new_obj_det_id=added.new_detection_id,
        app_user_id=setup.user1.id,
        corrected_taxonomy_id=setup.mouse.id,
        action="add",
    )

    compute(get_session, det_threshold=0.8, clas_threshold=0.8)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.mouse.id): (2, 1.0),
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.9),
    }


def test_removed_detection_stays_removed_with_thresholds(get_session, setup):
    image = add_image(get_session, setup, at(10))
    removed = add_detection(get_session, setup, image, [(setup.rat, 0.9)])
    add_detection_correction(get_session, setup, image, removed, action="remove")

    compute(get_session, det_threshold=0.5, clas_threshold=0.5)

    assert daily_results(get_session) == {}


def test_late_images_use_thresholds_of_the_rows_of_their_camera(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)

    # passes the old threshold, not the new one
    late = add_image(get_session, setup, at(11))
    add_detection(get_session, setup, late, [(setup.rat, 0.6)])
    add_detection(get_session, setup, late, [(setup.mouse, 0.6)])
    # below the old threshold
    add_detection(get_session, setup, late, [(setup.mouse, 0.4)])
    compute(get_session, clas_threshold=0.9)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (2, 0.65),
        (setup.camera1.id, setup.det_model.id, setup.mouse.id): (1, 0.6),
    }
    assert set(row_thresholds(get_session).values()) == {(0.0, 0.5)}


def test_camera_without_rows_of_the_day_uses_current_thresholds(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)

    other_camera = add_image(get_session, setup, at(11), camera=setup.camera2)
    add_detection(get_session, setup, other_camera, [(setup.rat, 0.8)])
    compute(get_session, clas_threshold=0.6)

    assert row_thresholds(get_session) == {
        (setup.camera1.id, setup.rat.id): (0.0, 0.5),
        (setup.camera2.id, setup.rat.id): (0.0, 0.6),
    }


def test_recompute_replaces_rows_with_current_thresholds(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    add_detection(get_session, setup, image, [(setup.mouse, 0.4)])
    compute(get_session, clas_threshold=0.5)
    assert set(daily_results(get_session)) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id)
    }

    compute(get_session, recompute=True, det_threshold=0.1, clas_threshold=0.2)

    assert row_thresholds(get_session) == {
        (setup.camera1.id, setup.rat.id): (0.1, 0.2),
        (setup.camera1.id, setup.mouse.id): (0.1, 0.2),
    }

    # a higher threshold removes the rows of the species it filters out
    compute(get_session, recompute=True, clas_threshold=0.9)
    assert daily_results(get_session) == {}


def test_recompute_of_a_camera_leaves_other_cameras(get_session, setup):
    for camera in (setup.camera1, setup.camera2):
        image = add_image(get_session, setup, at(10), camera=camera)
        add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)

    compute(get_session, recompute=True, camera_id=setup.camera1.id, clas_threshold=0.6)

    assert row_thresholds(get_session) == {
        (setup.camera1.id, setup.rat.id): (0.0, 0.6),
        (setup.camera2.id, setup.rat.id): (0.0, 0.5),
    }


@pytest.mark.parametrize("env_threshold", [None, "0.3"])
def test_correction_recompute_keeps_thresholds_of_its_rows(
    get_session, setup, monkeypatch, env_threshold
):
    """Also if the dashboard has no or other thresholds in its environment."""
    image = add_image(get_session, setup, at(10))
    removed = add_detection(get_session, setup, image, [(setup.rat, 0.9)])
    add_detection(get_session, setup, image, [(setup.rat, 0.8)])
    add_detection(get_session, setup, image, [(setup.mouse, 0.4)])
    compute(get_session, clas_threshold=0.5)

    if env_threshold is not None:
        monkeypatch.setenv("CLAS_CONF_THRESHOLD", env_threshold)
    add_detection_correction(get_session, setup, image, removed, action="remove")

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.8)
    }
    assert set(row_thresholds(get_session).values()) == {(0.0, 0.5)}


def test_correction_recompute_without_rows_uses_thresholds_of_the_environment(
    get_session, setup, monkeypatch
):
    image = add_image(get_session, setup, at(10))
    detection = add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.9)  # everything is filtered
    assert daily_results(get_session) == {}

    monkeypatch.setenv("CLAS_CONF_THRESHOLD", "0.3")
    add_classification_correction(get_session, setup, setup.mouse, detection)

    assert row_thresholds(get_session) == {
        (setup.camera1.id, setup.mouse.id): (0.0, 0.3)
    }


def test_recompute_without_keep_thresholds_uses_thresholds_of_the_environment(
    get_session, setup, monkeypatch
):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.7)])
    compute(get_session, clas_threshold=0.5)

    monkeypatch.setenv("CLAS_CONF_THRESHOLD", "0.3")
    compute(get_session, recompute=True)

    assert row_thresholds(get_session) == {(setup.camera1.id, setup.rat.id): (0.0, 0.3)}
