import pytest

from dashboard.db import (
    camera,
    taxonomy,
    analysis_result,
    ml_model,
    detection,
    classification,
    app_user,
    image,
)


@pytest.mark.parametrize(
    "crud, fixture_name, sample_data",
    [
        (ml_model.ml_model_crud, "created_ml_model", "ml_model_data"),
    ],
)
def test_add_return_added_row(request, crud, fixture_name, sample_data):
    created_item = request.getfixturevalue(fixture_name)()

    sample_data = request.getfixturevalue(sample_data)

    assert created_item.id is not None

    for field, expected_value in sample_data["create"].items():
        actual_value = getattr(created_item, field)
        assert actual_value == expected_value


@pytest.mark.parametrize(
    "crud, fixture_name",
    [
        (camera.camera_crud, "created_camera"),
        (camera.camera_location_history_crud, "created_camera"),
        (image.image_crud, "created_image"),
        (ml_model.ml_model_crud, "created_ml_model"),
        (detection.detection_crud, "created_object_detection"),
    ],
)
def test_select_and_get_return_saved_rows(request, get_session, crud, fixture_name):
    created_item = request.getfixturevalue(fixture_name)()

    items = crud.select(get_session)

    assert len(items) == 1
    assert items[0].id == created_item.id

    fetched_item = crud.get(get_session, created_item.id)
    assert fetched_item is not None
    assert fetched_item.id == created_item.id


@pytest.mark.parametrize(
    "crud, fixture_name,",
    [
        (camera.camera_crud, "created_multi_cameras"),
        (camera.camera_location_history_crud, "created_multi_cameras"),
        (image.image_crud, "created_multi_images"),
        (ml_model.ml_model_crud, "created_multi_ml_models"),
        (detection.detection_crud, "created_multi_object_detections"),
    ],
)
def test_filter_returns_filtered_rows(request, get_session, crud, fixture_name):
    # filter empty table, return empty list
    filtered_items = crud.filter(get_session, id=1)
    assert len(filtered_items) == 0

    # filter by ID of the first created model
    created_item = request.getfixturevalue(fixture_name)()

    filters = {"id": created_item[0].id}
    filtered_items = crud.filter(get_session, **filters)

    assert len(filtered_items) == 1
    assert filtered_items[0].id == created_item[0].id

    # no filters provided, raise ValueError
    with pytest.raises(ValueError):
        crud.filter(get_session)

    # no match, return empty list
    filters = {"id": -1}  # assuming -1 is an invalid ID
    filtered_items = crud.filter(get_session, **filters)
    assert len(filtered_items) == 0


@pytest.mark.parametrize(
    "crud, fixture_name, sample_data",
    [
        (ml_model.ml_model_crud, "created_ml_model", "ml_model_data"),
    ],
)
def test_update_fields(request, get_session, crud, fixture_name, sample_data):
    created_item = request.getfixturevalue(fixture_name)()
    sample_data = request.getfixturevalue(sample_data)

    # update with no changes, return the same object
    updated_item_no_changes = crud.update(
        get_session, created_item.id, allowed_fields=None
    )
    assert updated_item_no_changes is not None
    assert updated_item_no_changes.id == created_item.id
    for field in sample_data["create"].keys():
        actual_value = getattr(updated_item_no_changes, field)
        expected_value = getattr(created_item, field)
        assert actual_value == expected_value

    # update with unexpected fields, raise ValueError
    with pytest.raises(ValueError):
        crud.update(
            get_session, created_item.id, allowed_fields=None, unexpected_field="value"
        )

    # non existent ID, return None
    non_existent_id = -1  # assuming -1 is an invalid ID
    updated_item_non_existent = crud.update(
        get_session, non_existent_id, allowed_fields=None, **sample_data["update"]
    )
    assert updated_item_non_existent is None

    # invalid allowed_fields, raise ValueError
    with pytest.raises(ValueError):
        crud.update(
            get_session,
            created_item.id,
            allowed_fields={"invalid_field"},
            **sample_data["update"],
        )

    # update with new data
    updated_item = crud.update(
        get_session, created_item.id, allowed_fields=None, **sample_data["update"]
    )

    assert updated_item is not None
    for field, expected_value in sample_data["update"].items():
        actual_value = getattr(updated_item, field)
        assert actual_value == expected_value


@pytest.mark.parametrize(
    "crud, fixture_name,",
    [
        (camera.camera_crud, "created_camera"),
        (image.image_crud, "created_image"),
        (ml_model.ml_model_crud, "created_ml_model"),
        (detection.detection_crud, "created_object_detection"),
    ],
)
def test_delete_removes_row(request, get_session, crud, fixture_name):
    created_item = request.getfixturevalue(fixture_name)()

    deleted_item = crud.delete(get_session, created_item.id)

    assert deleted_item is True

    fetched_item = crud.get(get_session, created_item.id)
    assert fetched_item is None
