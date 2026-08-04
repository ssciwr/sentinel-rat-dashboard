from dashboard.db import detection, camera, image, ml_model
from dashboard.db.data_model import ObjectDetection
import pytest


def _add_object_detection(
    session, camera_data, image_data, ml_model_data, detection_data
):
    camera.add_camera(session, **camera_data["create"])
    image.add_image_capture(session, **image_data["create"])
    ml_model.add_ml_model(session, **ml_model_data["create"])
    return detection.add_object_detection(session, **detection_data["create"])


def test_add_object_detection_creates_row(
    get_session, camera_data, image_data, ml_model_data, object_detection_data
):
    created_detection = _add_object_detection(
        get_session, camera_data, image_data, ml_model_data, object_detection_data
    )

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


def test_select_and_get_object_detection_return_saved_rows(
    get_session, camera_data, image_data, ml_model_data, object_detection_data
):
    created_detection = _add_object_detection(
        get_session, camera_data, image_data, ml_model_data, object_detection_data
    )

    detections = detection.select_object_detections(get_session)

    assert len(detections) == 1
    assert detections[0].id == created_detection.id
    assert (
        detections[0].image_capture_id
        == object_detection_data["create"]["image_capture_id"]
    )

    fetched_detection = detection.get_object_detection(
        get_session, created_detection.id
    )
    assert fetched_detection is not None
    assert fetched_detection.id == created_detection.id
    assert (
        fetched_detection.detected_class
        == object_detection_data["create"]["detected_class"]
    )


def test_get_object_detections_by_filter_returns_filtered_rows(
    get_session, camera_data, image_data, ml_model_data, object_detection_data
):
    created_detection1 = _add_object_detection(
        get_session, camera_data, image_data, ml_model_data, object_detection_data
    )

    created_detection2 = detection.add_object_detection(
        get_session, **object_detection_data["create_another"]
    )

    filtered_detections = detection.get_object_detections_by_filter(
        get_session, detected_class=object_detection_data["create"]["detected_class"]
    )

    assert len(filtered_detections) == 1
    assert filtered_detections[0].id == created_detection1.id
    assert (
        filtered_detections[0].detected_class
        == object_detection_data["create"]["detected_class"]
    )

    filtered_detections_all = detection.get_object_detections_by_filter(
        get_session, det_model_id=1
    )
    assert len(filtered_detections_all) == 2


def test_get_object_detections_by_filter_raises_value_error_when_no_filters(
    get_session,
):
    with pytest.raises(ValueError):
        detection.get_object_detections_by_filter(get_session)


def test_update_object_detection_updates_fields(
    get_session, camera_data, image_data, ml_model_data, object_detection_data
):
    created_detection = _add_object_detection(
        get_session, camera_data, image_data, ml_model_data, object_detection_data
    )

    updated_detection = detection.update_object_detection(
        get_session, created_detection.id, **object_detection_data["update"]
    )

    assert updated_detection is not None
    assert updated_detection.id == created_detection.id
    assert updated_detection.confidence == object_detection_data["update"]["confidence"]
    assert (
        updated_detection.detected_class
        == object_detection_data["update"]["detected_class"]
    )


def test_update_object_detection_with_no_changes_returns_same_object(
    get_session, camera_data, image_data, ml_model_data, object_detection_data
):
    created_detection = _add_object_detection(
        get_session, camera_data, image_data, ml_model_data, object_detection_data
    )

    updated_detection = detection.update_object_detection(
        get_session, created_detection.id
    )

    assert updated_detection is not None
    assert updated_detection.id == created_detection.id
    assert updated_detection.confidence == created_detection.confidence


def test_update_object_detection_with_unexpected_fields_raises_error(
    get_session, camera_data, image_data, ml_model_data, object_detection_data
):
    created_detection = _add_object_detection(
        get_session, camera_data, image_data, ml_model_data, object_detection_data
    )

    with pytest.raises(ValueError):
        detection.update_object_detection(
            get_session, created_detection.id, unexpected_field="value"
        )


def test_update_object_detection_with_nonexistent_id_returns_none(
    get_session, camera_data, image_data, ml_model_data, object_detection_data
):
    created_detection = _add_object_detection(
        get_session, camera_data, image_data, ml_model_data, object_detection_data
    )

    updated_detection = detection.update_object_detection(
        get_session, created_detection.id + 1
    )
    assert updated_detection is None


def test_delete_object_detection_removes_row(
    get_session, camera_data, image_data, ml_model_data, object_detection_data
):
    created_detection = _add_object_detection(
        get_session, camera_data, image_data, ml_model_data, object_detection_data
    )

    assert detection.delete_object_detection(get_session, created_detection.id) is True

    deleted_detection = detection.get_object_detection(
        get_session, created_detection.id
    )
    assert deleted_detection is None
