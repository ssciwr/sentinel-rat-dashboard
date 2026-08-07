from dashboard.db import camera_crud, camera_location_history_crud
from dashboard.db.data_model import Camera, CameraLocationHistory
import pytest


def test_add_camera_creates_camera_and_initial_history(
    get_session, created_camera, camera_data, location_text, point_str
):

    created_camera = created_camera()

    assert created_camera.id is not None
    assert created_camera.name == camera_data["create"]["name"]
    assert created_camera.description == camera_data["create"]["description"]
    assert created_camera.status == camera_data["create"]["status"]
    assert location_text(get_session, Camera, created_camera.id) == point_str.format(
        camera_data["create"]["location"][0], camera_data["create"]["location"][1]
    )

    histories = camera_location_history_crud.get_by_camera(
        get_session, created_camera.id
    )
    assert len(histories) == 1
    assert histories[0].camera_id == created_camera.id
    assert histories[0].valid_to is None
    assert location_text(
        get_session, CameraLocationHistory, histories[0].id
    ) == point_str.format(
        camera_data["create"]["location"][0], camera_data["create"]["location"][1]
    )


def test_update_camera_updates_fields_and_location_history(
    get_session, created_camera, camera_data, location_text, point_str
):
    created_camera = created_camera()

    updated_camera = camera_crud.update(
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

    histories = camera_location_history_crud.get_by_camera(
        get_session,
        created_camera.id,
    )
    assert len(histories) == 2
    assert histories[0].valid_to is None  # most recent history
    assert histories[1].valid_to is not None
    assert location_text(
        get_session, CameraLocationHistory, histories[0].id  # most recent history
    ) == point_str.format(
        camera_data["update"]["location"][0], camera_data["update"]["location"][1]
    )


def test_update_camera_with_same_location_does_not_create_new_history(
    get_session, created_camera, camera_data, location_text, point_str
):
    created_camera = created_camera()

    # Update the camera with the same location
    updated_camera = camera_crud.update(
        get_session,
        created_camera.id,
        name=camera_data["update"]["name"],
        description=camera_data["update"]["description"],
        status=camera_data["update"]["status"],
        location=camera_data["create"]["location"],  # same as initial location
    )

    assert updated_camera is not None
    assert updated_camera.id == created_camera.id
    assert updated_camera.name == camera_data["update"]["name"]
    assert updated_camera.description == camera_data["update"]["description"]
    assert updated_camera.status == camera_data["update"]["status"]
    assert location_text(get_session, Camera, created_camera.id) == point_str.format(
        camera_data["create"]["location"][0], camera_data["create"]["location"][1]
    )

    histories = camera_location_history_crud.get_by_camera(
        get_session, created_camera.id
    )
    assert len(histories) == 1  # No new history should be added


def test_update_camera_with_no_changes_returns_same_object(get_session, created_camera):
    created_camera = created_camera()

    updated_camera = camera_crud.update(get_session, created_camera.id)

    assert updated_camera is not None
    assert updated_camera.id == created_camera.id
    assert updated_camera.name == created_camera.name
    assert updated_camera.description == created_camera.description
    assert updated_camera.status == created_camera.status

    histories = camera_location_history_crud.get_by_camera(
        get_session, created_camera.id
    )
    assert len(histories) == 1  # No new history should be added


def test_update_camera_with_unexpected_fields_raises_error(get_session, created_camera):
    created_camera = created_camera()

    with pytest.raises(ValueError):
        camera_crud.update(get_session, created_camera.id, unexpected_field="value")


def test_history_get_by_camera_returns_ordered_histories(
    get_session, created_camera, camera_data
):
    created_camera = created_camera()

    # Update the camera to create a second history entry
    camera_crud.update(get_session, created_camera.id, **camera_data["update"])

    histories = camera_location_history_crud.get_by_camera(
        get_session, created_camera.id
    )

    assert len(histories) == 2
    assert histories[0].valid_to is None  # most recent history
    assert histories[1].valid_to is not None  # older history


def test_history_update_valid_to_most_recent_history(
    get_session, created_camera, camera_data
):
    created_camera = created_camera()

    current_history = camera_location_history_crud.get_by_camera(
        get_session, created_camera.id
    )[0]

    assert current_history.valid_to is None

    # Update the camera to create a second history entry
    camera_crud.update(get_session, created_camera.id, **camera_data["update"])

    updated_history = camera_location_history_crud.get_by_camera(
        get_session, created_camera.id
    )[
        1
    ]  # the older history should now have a valid_to timestamp

    assert updated_history is not None
    assert updated_history.valid_to is not None


def test_delete_old_camera_history_removes_obsolete_histories(
    get_session, created_camera, camera_data
):
    created_camera = created_camera()

    # Update the camera to create a second history entry
    camera_crud.update(get_session, created_camera.id, **camera_data["update"])

    # Now delete obsolete histories (should keep the most recent one)
    deleted = camera_location_history_crud.delete_old_camera_history(
        get_session, created_camera.id
    )

    assert deleted is True

    histories = camera_location_history_crud.get_by_camera(
        get_session, created_camera.id
    )
    assert len(histories) == 1  # Only the most recent history should remain
    assert (
        histories[0].valid_to is None
    )  # The remaining history should be the most recent one


def test_refuse_direct_add_update_delete(get_session, created_camera):

    created_camera = created_camera()
    created_history = camera_location_history_crud.get_by_camera(
        get_session, created_camera.id
    )[0]

    with pytest.raises(NotImplementedError):
        camera_location_history_crud.add(
            get_session,
            camera_id=created_camera.id,
            location="POINT(7.1234 50.5678)",
        )

    with pytest.raises(NotImplementedError):
        camera_location_history_crud.update(
            get_session, created_history.id, {"valid_to": "2024-01-01T00:00:00Z"}
        )

    with pytest.raises(NotImplementedError):
        camera_location_history_crud.delete(get_session, created_history.id)
