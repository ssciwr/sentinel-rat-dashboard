from dashboard.db import detection_crud
import pytest


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
