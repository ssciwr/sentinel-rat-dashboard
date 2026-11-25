import pytest

from dashboard.db import camera_crud, camera_location_history_crud
from dashboard.db.data_model import Camera

save = camera_crud.save_coordinates
histories = camera_location_history_crud.get_by_camera


@pytest.mark.parametrize("description", [None, "Main entrance\nNorth-facing camera"])
# Initial camera is created/spawned with history
def test_save_camera_creates_history(get_session, description):
    values = dict(name="S1Z1-T3", latitude=7.001, longitude=81.001)
    camera = save(get_session, description=description, **values)
    rows = camera_crud.select_map_rows(get_session)
    assert (camera.name, camera.description) == ("S1Z1-T3", description)
    assert rows[0]["description"] == (description or "")
    assert (rows[0]["latitude"], rows[0]["longitude"]) == (7.001, 81.001)
    assert len(histories(get_session, camera.id)) == 1



@pytest.mark.parametrize(
    "name,lat,lon",
    [
        ("", 0, 0),
        ("x" * 256, 0, 0),
        ("new", 90.1, 0),
        ("new", 0, -180.1),
        ("new", float("nan"), 0),
        ("new", 0, float("inf")),
    ],
)

# We expect errors for invalid save attempts
def test_invalid_settings_preserve_camera(get_session, created_camera, name, lat, lon):
    camera = created_camera()
    with pytest.raises(ValueError):
        save(get_session, name=name, latitude=lat, longitude=lon)
    assert len(camera_crud.select(get_session)) == 1
    assert get_session.get(Camera, camera.id).name == camera.name
    assert len(histories(get_session, camera.id)) == 1


# Check edits cannot save to another camera (ID)
def test_duplicate_name_preserves_other_camera(get_session, created_multi_cameras):
    first, second = created_multi_cameras()
    with pytest.raises(ValueError):
        save(get_session, camera_id=first.id, name=second.name, latitude=0, longitude=0)
    assert len(camera_crud.select(get_session)) == 2
    assert get_session.get(Camera, second.id).name == second.name
    assert len(histories(get_session, first.id)) == 1


@pytest.mark.parametrize("status", ["active", "inactive"])
# toggling status saves it. Note, even though we only have two statuses now,
# this has been left as open to setting the status to the users choice rather than a binary "is_active" toggle as the current DB implementation
# when writing the add/edit camera settings boilerplate (partially with AI) had multiple string statuses rather than a boolean, so it allows this PR
# to be opened now and keeps the codebase open for future statuses.
def test_camera_settings_include_status(get_session, status):
    values = dict(name="S1Z1-T3", latitude=7.001, longitude=81.001, status=status)
    camera = save(get_session, **values)
    row = camera_crud.select_map_rows(get_session)[0]
    assert camera.status == status
    assert row["status"] == status
    assert len(histories(get_session, camera.id)) == 1


@pytest.mark.parametrize("status", ["inactive"])
# AI-Generated
# Preserve status when another caller saves only camera coordinates.
def test_omitted_status_preserves_existing_status(get_session, status):
    values = dict(name="S1Z1-T3", latitude=7.001, longitude=81.001)
    camera = save(get_session, status=status, **values)
    values["name"] = "Renamed"
    updated = save(get_session, camera_id=camera.id, **values)
    assert updated.id == camera.id
    assert updated.status == status
    assert len(histories(get_session, camera.id)) == 1

def test_status_change_preserves_camera_history(get_session, created_camera):
    camera = created_camera()
    values = dict(name=camera.name, latitude=7.001, longitude=81.001)
    updated = save(get_session, camera_id=camera.id, status="inactive", **values)
    assert updated.id == camera.id
    assert updated.status == "inactive"
    assert len(histories(get_session, camera.id)) == 1
