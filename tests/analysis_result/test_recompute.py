import pytest
from sqlalchemy import select

from dashboard.db import (
    classification_correction_crud,
    classification_crud,
    detection_correction_crud,
    image_crud,
)
from dashboard.db.data_model import ClassificationCorrection

from .helpers import (
    add_classification_correction,
    add_detection,
    add_detection_correction,
    add_image,
    at,
    compute,
    daily_results,
)


def test_recompute_rebuilds_day_and_drops_stale_rows(get_session, setup):
    image = add_image(get_session, setup, at(10))
    detection = add_detection(get_session, setup, image, [(setup.rat, 0.6)])
    compute(get_session)
    # a new, more confident classification doesn't trigger a recompute by itself
    classification_crud.add(
        get_session,
        object_detection_id=detection.id,
        taxonomy_id=setup.mouse.id,
        clas_model_id=setup.clas_model2.id,
        confidence=0.8,
    )

    compute(get_session)
    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.6)
    }

    compute(get_session, recompute=True)
    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.mouse.id): (1, 0.8)
    }


def test_recompute_includes_moved_images(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.6)])
    add_detection(get_session, setup, image, [(setup.mouse, 0.4)])
    compute(get_session)
    image_crud.mark_image_as_moved(get_session, image.id)

    compute(get_session, recompute=True, clas_threshold=0.5)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.6)
    }


def test_recompute_refused_when_images_are_gone(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.6)])
    compute(get_session)
    image_crud.delete(get_session, image.id)

    with pytest.raises(ValueError, match="gone"):
        compute(get_session, recompute=True)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.6)
    }


def test_correction_after_aggregation_recomputes_its_camera_and_day(get_session, setup):
    image = add_image(get_session, setup, at(10))
    detection = add_detection(get_session, setup, image, [(setup.rat, 0.6)])
    other_image = add_image(get_session, setup, at(10), camera=setup.camera2)
    add_detection(get_session, setup, other_image, [(setup.rat, 0.5)])
    compute(get_session)

    correction = add_classification_correction(
        get_session, setup, setup.mouse, detection
    )

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.mouse.id): (1, 1.0),
        (setup.camera2.id, setup.det_model.id, setup.rat.id): (1, 0.5),
    }

    classification_correction_crud.update(
        get_session, correction.id, corrected_taxonomy_id=setup.rat.id
    )

    assert daily_results(get_session)[
        (setup.camera1.id, setup.det_model.id, setup.rat.id)
    ] == (1, 1.0)

    classification_correction_crud.delete(get_session, correction.id)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.6),
        (setup.camera2.id, setup.det_model.id, setup.rat.id): (1, 0.5),
    }

    detection_correction = add_detection_correction(
        get_session, setup, image, detection
    )
    detection_correction_crud.update(
        get_session, detection_correction.id, action="remove"
    )

    assert daily_results(get_session) == {
        (setup.camera2.id, setup.det_model.id, setup.rat.id): (1, 0.5)
    }

    detection_correction_crud.delete(get_session, detection_correction.id)

    assert daily_results(get_session)[
        (setup.camera1.id, setup.det_model.id, setup.rat.id)
    ] == (1, 0.6)


def test_correction_before_aggregation_does_not_aggregate(get_session, setup):
    image = add_image(get_session, setup, at(10))
    detection = add_detection(get_session, setup, image, [(setup.rat, 0.6)])

    add_classification_correction(get_session, setup, setup.mouse, detection)

    assert daily_results(get_session) == {}
    assert image_crud.get_images_to_move(get_session) == []


def test_correction_is_rolled_back_when_recompute_fails(
    get_session, setup, monkeypatch
):
    image = add_image(get_session, setup, at(10))
    detection = add_detection(get_session, setup, image, [(setup.rat, 0.6)])
    compute(get_session)
    monkeypatch.setenv("CLAS_CONF_THRESHOLD", "high")

    with pytest.raises(ValueError, match="CLAS_CONF_THRESHOLD"):
        add_classification_correction(get_session, setup, setup.mouse, detection)

    assert get_session.scalars(select(ClassificationCorrection)).all() == []
    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.rat.id): (1, 0.6)
    }


def test_correction_of_moved_image_updates_daily_results(get_session, setup):
    image = add_image(get_session, setup, at(10))
    detection = add_detection(get_session, setup, image, [(setup.rat, 0.6)])
    compute(get_session)
    image_crud.mark_image_as_moved(get_session, image.id)

    add_classification_correction(get_session, setup, setup.mouse, detection)

    assert daily_results(get_session) == {
        (setup.camera1.id, setup.det_model.id, setup.mouse.id): (1, 1.0)
    }
