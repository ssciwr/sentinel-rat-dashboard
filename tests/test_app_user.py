from dashboard.db import app_user
from dashboard.db.data_model import AppUser
import pytest


def test_add_app_user_creates_row(get_session, app_user_data):
    created_user = app_user.add_app_user(get_session, **app_user_data["create"])

    assert created_user.id is not None
    assert created_user.username == app_user_data["create"]["username"]
    assert created_user.full_name == app_user_data["create"]["full_name"]
    assert created_user.is_active == app_user_data["create"]["is_active"]

    created_user_wo_optional_fields = app_user.add_app_user(
        get_session, **app_user_data["create_wo_optional_fields"]
    )

    assert created_user_wo_optional_fields.id is not None
    assert (
        created_user_wo_optional_fields.username
        == app_user_data["create_wo_optional_fields"]["username"]
    )
    assert created_user_wo_optional_fields.full_name is None
    assert created_user_wo_optional_fields.is_active is True


def test_select_and_get_app_user_return_saved_rows(get_session, app_user_data):
    created_user = app_user.add_app_user(get_session, **app_user_data["create"])

    users = app_user.select_app_users(get_session)

    assert len(users) == 1
    assert users[0].id == created_user.id
    assert users[0].username == app_user_data["create"]["username"]

    fetched_user = app_user.get_app_user(get_session, created_user.id)
    assert fetched_user is not None
    assert fetched_user.id == created_user.id
    assert fetched_user.full_name == app_user_data["create"]["full_name"]


def test_get_app_users_by_filter_returns_filtered_rows(get_session, app_user_data):
    app_user.add_app_user(get_session, **app_user_data["create"])
    app_user.add_app_user(get_session, **app_user_data["create_wo_optional_fields"])

    filtered_users = app_user.get_app_users_by_filter(
        get_session, username=app_user_data["create"]["username"]
    )

    assert len(filtered_users) == 1
    assert filtered_users[0].id == 1
    assert filtered_users[0].username == app_user_data["create"]["username"]

    filtered_users_active = app_user.get_app_users_by_filter(
        get_session, is_active=True
    )
    assert len(filtered_users_active) == 2


def test_get_app_users_by_filter_raises_value_error_when_no_filters(get_session):
    with pytest.raises(ValueError):
        app_user.get_app_users_by_filter(get_session)


def test_update_app_user_updates_fields(get_session, app_user_data):
    created_user = app_user.add_app_user(get_session, **app_user_data["create"])

    updated_user = app_user.update_app_user(
        get_session, created_user.id, **app_user_data["update"]
    )

    assert updated_user is not None
    assert updated_user.id == created_user.id
    assert updated_user.full_name == app_user_data["update"]["full_name"]
    assert updated_user.is_active == app_user_data["update"]["is_active"]


def test_update_app_user_with_no_changes_returns_same_object(
    get_session, app_user_data
):
    created_user = app_user.add_app_user(get_session, **app_user_data["create"])

    updated_user = app_user.update_app_user(get_session, created_user.id)

    assert updated_user is not None
    assert updated_user.id == created_user.id
    assert updated_user.username == created_user.username
    assert updated_user.is_active == created_user.is_active


def test_update_app_user_with_unexpected_fields_raises_error(
    get_session, app_user_data
):
    created_user = app_user.add_app_user(get_session, **app_user_data["create"])

    with pytest.raises(ValueError):
        app_user.update_app_user(get_session, created_user.id, unexpected_field="value")


def test_update_app_user_with_nonexistent_id_returns_none(get_session, app_user_data):
    created_user = app_user.add_app_user(get_session, **app_user_data["create"])

    updated_user = app_user.update_app_user(get_session, created_user.id + 1)
    assert updated_user is None


def test_delete_app_user_removes_row(get_session, app_user_data):
    created_user = app_user.add_app_user(get_session, **app_user_data["create"])

    assert app_user.delete_app_user(get_session, created_user.id) is True

    deleted_user = app_user.get_app_user(get_session, created_user.id)
    assert deleted_user is None
