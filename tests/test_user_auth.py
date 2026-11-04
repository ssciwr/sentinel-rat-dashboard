import pytest

from dashboard.db import app_user_crud

# Test credential storage with a placeholder; R login tests verify real hashes.
STORED_PASSWORD = "test-only-encoded-password"


# AI-Generated
# Store credentials for a new active account.
def test_set_password_creates_database_credentials(get_session):
    user = app_user_crud.set_password(
        get_session, username="new-user", password=STORED_PASSWORD
    )
    login = app_user_crud.get_login(get_session, "new-user")
    assert login["app_user_id"] == user.id
    assert login["password"] == STORED_PASSWORD
    assert login["is_active"] is True


# AI-Generated
# Preserve an existing identity, profile, and disabled state when setting a password.
def test_set_password_preserves_existing_user(get_session, created_app_user):
    user = created_app_user()
    app_user_crud.update(get_session, user.id, is_active=False)
    updated = app_user_crud.set_password(
        get_session, username=user.username, password=STORED_PASSWORD
    )
    assert updated.id == user.id
    assert updated.is_active is False
    assert updated.full_name == "Test User"


@pytest.mark.parametrize("username", ["missing", "testuser ", "' OR 1=1 --"])
# AI-Generated
# Keep account lookups exact without changing stored users.
def test_unknown_login_does_not_match_another_user(
    get_session, created_app_user, username
):
    user = created_app_user()
    timestamp = user.updated_at
    login = app_user_crud.get_login(get_session, username)
    assert login is None
    assert len(app_user_crud.select(get_session)) == 1
    assert user.updated_at == timestamp


# AI-Generated
# Leave historical users without a usable password until one is explicitly set.
def test_existing_user_without_credentials_cannot_supply_a_password(
    get_session, created_app_user
):
    user = created_app_user()
    app_user_crud.update(get_session, user.id, password="")
    login = app_user_crud.get_login(get_session, user.username)
    assert login["app_user_id"] == user.id
    assert login["password"] is None
    assert login["is_active"] is True


# AI-Generated
# Preserve stored credentials when updating the user's profile.
def test_profile_update_preserves_password(get_session, created_app_user):
    user = created_app_user()
    app_user_crud.set_password(
        get_session, username=user.username, password=STORED_PASSWORD
    )
    updated = app_user_crud.update(get_session, user.id, full_name="Updated User")
    assert updated.password == STORED_PASSWORD
    assert updated.full_name == "Updated User"
    assert updated.id == user.id


@pytest.mark.parametrize("username", ["", " ", "x" * 51])
# AI-Generated
# Reject invalid account names without changing an existing user.
def test_invalid_username_preserves_user(get_session, created_app_user, username):
    user = created_app_user()
    with pytest.raises(ValueError, match="Username"):
        app_user_crud.set_password(
            get_session, username=username, password=STORED_PASSWORD
        )
    assert user.full_name == "Test User"
    assert user.password == "encoded-password"
    assert len(app_user_crud.select(get_session)) == 1
