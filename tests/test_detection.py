import pytest

from dashboard.db import detection_correction_crud, detection_crud


# tests for ObjectDetectionCRUD
def test_add_object_detection_creates_row(
    created_object_detection, object_detection_data
):
    created_detection = created_object_detection()

    assert created_detection.id is not None
    assert (
        created_detection.image_capture_id
        == object_detection_data["create"]["image_capture_id"]
    )
    assert (
        created_detection.det_model_id
        == object_detection_data["create"]["det_model_id"]
    )
    assert created_detection.confidence == object_detection_data["create"]["confidence"]
    assert created_detection.bbox == object_detection_data["create"]["bbox"]
    assert (
        created_detection.detected_class
        == object_detection_data["create"]["detected_class"]
    )


def test_refuse_direct_update(
    get_session, created_object_detection, object_detection_data
):
    created_detection = created_object_detection()

    with pytest.raises(NotImplementedError):
        detection_crud.update(
            get_session,
            created_detection.id,
            **object_detection_data["update"],
        )


# test for DetectionCorrectionCRUD
def test_add_detection_correction_creates_row(
    created_detection_correction, detection_correction_data
):
    created_correction = created_detection_correction()

    assert created_correction.id is not None
    for field, expected_value in detection_correction_data["create"].items():
        actual_value = getattr(created_correction, field)
        assert actual_value == expected_value
    assert created_correction.new_detection_id is None


def test_add_detection_correction_with_add_action(
    created_multi_detection_corrections, detection_correction_data
):
    multi_corrections = created_multi_detection_corrections()
    created_correction = multi_corrections[0]
    created_correction_add = multi_corrections[1]

    assert (
        created_correction.object_detection_id
        == detection_correction_data["create"]["object_detection_id"]
    )
    assert created_correction_add.object_detection_id is None
    assert created_correction_add.action == "add"
    assert created_correction_add.new_detection_id == 1


def test_add_detection_correction_with_errors(
    get_session, created_object_detection, detection_correction_data
):
    # create first valid item
    _ = created_object_detection()

    # object_detection_id is None and action is not "add"
    sample_data = detection_correction_data["create"].copy()
    sample_data["object_detection_id"] = None
    sample_data["action"] = "update"
    with pytest.raises(ValueError):
        detection_correction_crud.add(get_session, **sample_data)

    # object_detection_id is not None and action is "add"
    sample_data = detection_correction_data["create"].copy()
    sample_data["action"] = "add"
    with pytest.raises(ValueError):
        detection_correction_crud.add(get_session, **sample_data)


def test_update_detection_correction_update_fields(
    get_session, created_detection_correction, detection_correction_data
):
    created_correction = created_detection_correction()

    last_updated_before = created_correction.last_updated

    updated_correction = detection_correction_crud.update(
        get_session, created_correction.id, **detection_correction_data["update"]
    )

    last_updated_after = updated_correction.last_updated

    assert updated_correction is not None
    assert updated_correction.id == created_correction.id
    for field, value in detection_correction_data["update"].items():
        actual_value = getattr(updated_correction, field)
        assert actual_value == value
    assert last_updated_after > last_updated_before
