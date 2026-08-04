from dashboard.db import ml_model
from dashboard.db.data_model import MLModel
import pytest


def test_add_ml_model_creates_row(get_session, ml_model_data):
    created_model = ml_model.add_ml_model(get_session, **ml_model_data["create"])

    assert created_model.id is not None
    assert created_model.name == ml_model_data["create"]["name"]
    assert created_model.task == ml_model_data["create"]["task"]
    assert created_model.version == ml_model_data["create"]["version"]
    assert created_model.description == ml_model_data["create"]["description"]

    created_model_wo_optional_fields = ml_model.add_ml_model(
        get_session, **ml_model_data["create_wo_optional_fields"]
    )

    assert created_model_wo_optional_fields.id is not None
    assert (
        created_model_wo_optional_fields.name
        == ml_model_data["create_wo_optional_fields"]["name"]
    )
    assert (
        created_model_wo_optional_fields.task
        == ml_model_data["create_wo_optional_fields"]["task"]
    )
    assert created_model_wo_optional_fields.version is None
    assert created_model_wo_optional_fields.description is None


def test_select_and_get_ml_model_return_saved_rows(get_session, ml_model_data):
    created_model = ml_model.add_ml_model(get_session, **ml_model_data["create"])

    models = ml_model.select_ml_models(get_session)

    assert len(models) == 1
    assert models[0].id == created_model.id
    assert models[0].name == ml_model_data["create"]["name"]

    fetched_model = ml_model.get_ml_model(get_session, created_model.id)
    assert fetched_model is not None
    assert fetched_model.id == created_model.id
    assert fetched_model.description == ml_model_data["create"]["description"]


def test_get_ml_models_by_filter_returns_filtered_rows(get_session, ml_model_data):
    created_model = ml_model.add_ml_model(get_session, **ml_model_data["create"])
    created_model_wo_optional_fields = ml_model.add_ml_model(
        get_session, **ml_model_data["create_wo_optional_fields"]
    )

    filtered_models = ml_model.get_ml_models_by_filter(
        get_session, name=ml_model_data["create"]["name"]
    )

    assert len(filtered_models) == 1
    assert filtered_models[0].id == created_model.id
    assert filtered_models[0].name == ml_model_data["create"]["name"]

    filtered_models_wo_optional_fields = ml_model.get_ml_models_by_filter(
        get_session, task=ml_model_data["create_wo_optional_fields"]["task"]
    )

    assert len(filtered_models_wo_optional_fields) == 1
    assert (
        filtered_models_wo_optional_fields[0].id == created_model_wo_optional_fields.id
    )
    assert (
        filtered_models_wo_optional_fields[0].task
        == ml_model_data["create_wo_optional_fields"]["task"]
    )


def test_get_ml_models_by_filter_raises_value_error_when_no_filters(get_session):
    with pytest.raises(ValueError) as exc_info:
        ml_model.get_ml_models_by_filter(get_session)

    assert str(exc_info.value) == (
        "At least one filter must be provided."
        "To get all rows, use select_ml_models() instead."
    )


def test_update_ml_model_updates_fields(get_session, ml_model_data):
    created_model = ml_model.add_ml_model(get_session, **ml_model_data["create"])

    updated_model = ml_model.update_ml_model(
        get_session, created_model.id, **ml_model_data["update"]
    )

    assert updated_model is not None
    assert updated_model.id == created_model.id
    assert updated_model.name == ml_model_data["update"]["name"]
    assert updated_model.version == ml_model_data["update"]["version"]
    assert updated_model.description == ml_model_data["update"]["description"]


def test_update_ml_model_with_no_changes_returns_same_object(
    get_session, ml_model_data
):
    created_model = ml_model.add_ml_model(get_session, **ml_model_data["create"])

    updated_model = ml_model.update_ml_model(get_session, created_model.id)

    assert updated_model is not None
    assert updated_model.id == created_model.id
    assert updated_model.name == created_model.name
    assert updated_model.version == created_model.version
    assert updated_model.description == created_model.description


def test_update_ml_model_with_unexpected_fields_raises_error(
    get_session, ml_model_data
):
    created_model = ml_model.add_ml_model(get_session, **ml_model_data["create"])

    with pytest.raises(ValueError):
        ml_model.update_ml_model(
            get_session, created_model.id, unexpected_field="value"
        )


def test_update_ml_model_with_nonexistent_id_returns_none(get_session, ml_model_data):
    created_model = ml_model.add_ml_model(get_session, **ml_model_data["create"])

    updated_model = ml_model.update_ml_model(get_session, created_model.id + 1)

    assert updated_model is None


def test_delete_ml_model_removes_row(get_session, ml_model_data):
    created_model = ml_model.add_ml_model(get_session, **ml_model_data["create"])

    assert ml_model.delete_ml_model(get_session, created_model.id) is True

    deleted_model = ml_model.get_ml_model(get_session, created_model.id)
    assert deleted_model is None
