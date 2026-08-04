from dashboard.db import camera
from dashboard.db.data_model import Camera, CameraLocationHistory
import pytest


def test_add_camera_creates_camera_and_initial_history(
    get_session, camera_data, location_text, point_str
):
    created_camera = camera.add_camera(get_session, **camera_data["create"])

    assert created_camera.id is not None
    assert created_camera.name == camera_data["create"]["name"]
    assert created_camera.description == camera_data["create"]["description"]
    assert created_camera.status == camera_data["create"]["status"]
    assert location_text(get_session, Camera, created_camera.id) == point_str.format(
        camera_data["create"]["location"][0], camera_data["create"]["location"][1]
    )

    histories = camera.get_camera_location_history(get_session, created_camera.id)
    assert len(histories) == 1
    assert histories[0].camera_id == created_camera.id
    assert histories[0].valid_to is None
    assert location_text(
        get_session, CameraLocationHistory, histories[0].id
    ) == point_str.format(
        camera_data["create"]["location"][0], camera_data["create"]["location"][1]
    )


def test_select_and_get_camera_return_saved_rows(get_session, camera_data):
    created_camera = camera.add_camera(get_session, **camera_data["create"])

    cameras = camera.select_cameras(get_session)

    assert len(cameras) == 1
    assert cameras[0].id == created_camera.id
    assert cameras[0].name == camera_data["create"]["name"]

    fetched_camera = camera.get_camera(get_session, created_camera.id)
    assert fetched_camera is not None
    assert fetched_camera.id == created_camera.id
    assert fetched_camera.description == camera_data["create"]["description"]


def test_update_camera_updates_fields_and_location_history(
    get_session, camera_data, location_text, point_str
):
    created_camera = camera.add_camera(get_session, **camera_data["create"])

    updated_camera = camera.update_camera(
        get_session, created_camera.id, **camera_data["update"]
    )

    assert updated_camera is not None
    assert updated_camera.id == created_camera.id
    assert updated_camera.name == camera_data["update"]["name"]
    assert updated_camera.description == camera_data["update"]["description"]
    assert updated_camera.status == camera_data["update"]["status"]
    assert location_text(get_session, Camera, created_camera.id) == point_str.format(
        camera_data["update"]["location"][0], camera_data["update"]["location"][1]
    )

    histories = camera.get_camera_location_history(
        get_session,
        created_camera.id,
    )
    assert len(histories) == 2
    assert histories[0].valid_to is not None
    assert histories[1].valid_to is None
    assert location_text(
        get_session, CameraLocationHistory, histories[1].id
    ) == point_str.format(
        camera_data["update"]["location"][0], camera_data["update"]["location"][1]
    )


def test_update_camera_with_no_changes_returns_same_object(get_session, camera_data):
    created_camera = camera.add_camera(get_session, **camera_data["create"])

    updated_camera = camera.update_camera(get_session, created_camera.id)

    assert updated_camera is not None
    assert updated_camera.id == created_camera.id
    assert updated_camera.name == created_camera.name
    assert updated_camera.description == created_camera.description
    assert updated_camera.status == created_camera.status

    histories = camera.get_camera_location_history(get_session, created_camera.id)
    assert len(histories) == 1  # No new history should be added


def test_update_camera_with_unexpected_fields_raises_error(get_session, camera_data):
    created_camera = camera.add_camera(get_session, **camera_data["create"])

    with pytest.raises(ValueError):
        camera.update_camera(get_session, created_camera.id, unexpected_field="value")


def test_delete_helpers_remove_histories_and_camera(get_session, camera_data):
    created_camera = camera.add_camera(get_session, **camera_data["create"])

    assert camera.delete_camera_location_history(get_session, created_camera.id) is True
    assert camera.get_camera_location_history(get_session, created_camera.id) == []

    assert camera.delete_camera(get_session, created_camera.id) is True
    assert camera.get_camera(get_session, created_camera.id) is None
    assert camera.select_cameras(get_session) == []
