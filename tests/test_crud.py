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
    "crud, fixture_name",
    [
        (camera.camera_crud, "created_camera"),
        (camera.camera_location_history_crud, "created_camera"),
        (image.image_crud, "created_image"),
    ],
)
def test_select_and_get_return_saved_rows(request, get_session, crud, fixture_name):
    created_model = request.getfixturevalue(fixture_name)()

    models = crud.select(get_session)

    assert len(models) == 1
    assert models[0].id == created_model.id

    fetched_model = crud.get(get_session, created_model.id)
    assert fetched_model is not None
    assert fetched_model.id == created_model.id


@pytest.mark.parametrize(
    "crud, fixture_name,",
    [
        (camera.camera_crud, "created_multi_cameras"),
        (camera.camera_location_history_crud, "created_multi_cameras"),
        (image.image_crud, "created_multi_images"),
    ],
)
def test_filter_returns_filtered_rows(request, get_session, crud, fixture_name):
    # filter empty table, return empty list
    filtered_models = crud.filter(get_session, id=1)
    assert len(filtered_models) == 0

    # filter by ID of the first created model
    created_model = request.getfixturevalue(fixture_name)()

    filters = {"id": created_model[0].id}
    filtered_models = crud.filter(get_session, **filters)

    assert len(filtered_models) == 1
    assert filtered_models[0].id == created_model[0].id

    # no filters provided, raise ValueError
    with pytest.raises(ValueError):
        crud.filter(get_session)

    # no match, return empty list
    filters = {"id": -1}  # assuming -1 is an invalid ID
    filtered_models = crud.filter(get_session, **filters)
    assert len(filtered_models) == 0


@pytest.mark.parametrize(
    "crud, fixture_name,",
    [
        (camera.camera_crud, "created_camera"),
        (image.image_crud, "created_image"),
    ],
)
def test_delete_removes_row(request, get_session, crud, fixture_name):
    created_model = request.getfixturevalue(fixture_name)()

    deleted_model = crud.delete(get_session, created_model.id)

    assert deleted_model is True

    fetched_model = crud.get(get_session, created_model.id)
    assert fetched_model is None
