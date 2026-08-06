from dashboard.db import app_user_crud
import pytest


def test_add_app_user_creates_row(created_multi_app_users, app_user_data):
    created_users = created_multi_app_users()
    created_user = created_users[0]
    created_another_user = created_users[1]

    assert created_user.id is not None
    assert created_user.username == app_user_data["create"]["username"]
    assert created_user.full_name == app_user_data["create"]["full_name"]
    assert created_user.is_active == app_user_data["create"]["is_active"]

    assert created_another_user.id is not None
    assert created_another_user.username == app_user_data["create_another"]["username"]
    assert created_another_user.full_name is None
    assert created_another_user.is_active is True


def test_update_app_user_updates_fields(get_session, created_app_user, app_user_data):
    created_user = created_app_user()

    updated_at_before_update = created_user.updated_at

    updated_user = app_user_crud.update(
        get_session, created_user.id, **app_user_data["update"]
    )

    updated_at_after_update = updated_user.updated_at

    assert updated_user is not None
    assert updated_user.id == created_user.id
    assert updated_user.full_name == app_user_data["update"]["full_name"]
    assert updated_user.is_active == app_user_data["update"]["is_active"]
    assert updated_at_after_update > updated_at_before_update
