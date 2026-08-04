"""CRUD helpers for the app_user table"""

from typing import Any

from sqlalchemy import select, DateTime, func
from sqlalchemy.orm import Session

from .data_model import AppUser
from . import utils


def add_app_user(
    session: Session,
    *,
    username: str,
    full_name: str | None = None,
    is_active: bool = True,
    created_at: DateTime | None = None,
    updated_at: DateTime | None = None,
) -> AppUser:
    """Insert a new app_user row and return the persisted object."""

    app_user = AppUser(
        username=username,
        full_name=full_name,
        is_active=is_active,
    )

    if created_at is not None:
        app_user.created_at = created_at

    if updated_at is not None:
        app_user.updated_at = updated_at

    session.add(app_user)
    utils.commit(session)
    session.refresh(app_user)

    return app_user


def select_app_users(session: Session) -> list[AppUser]:
    """Return all app_user rows ordered by primary key."""

    statement = select(AppUser).order_by(AppUser.id)
    return list(session.execute(statement).scalars().all())


def get_app_user(session: Session, app_user_id: int) -> AppUser | None:
    """Return one app_user row by primary key."""

    return session.get(AppUser, app_user_id)


def get_app_users_by_filter(session: Session, **filters: Any) -> list[AppUser]:
    """Return a list of app_user rows filtered by the provided keyword arguments."""

    if not filters:
        raise ValueError(
            "At least one filter must be provided."
            "To select all app users, use `select_app_users()` instead."
        )

    statement = select(AppUser).filter_by(**filters).order_by(AppUser.id)
    return list(session.execute(statement).scalars().all())


def update_app_user(
    session: Session, app_user_id: int, **changes: Any
) -> AppUser | None:
    """Update an app_user row and return the refreshed object, or None if missing."""

    app_user = session.get(AppUser, app_user_id)
    if app_user is None:
        return None

    if not changes:
        return app_user

    allowed_fields = {"full_name", "is_active"}
    unexpected_fields = set(changes.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"Unsupported app_user fields: {sorted(unexpected_fields)}")

    for key, value in changes.items():
        setattr(app_user, key, value)

    # automatically update the updated_at timestamp
    app_user.updated_at = func.now()

    utils.commit(session)
    session.refresh(app_user)

    return app_user


def delete_app_user(session: Session, app_user_id: int) -> bool:
    """Delete an app_user row by primary key. Return True if deleted, False if not found."""

    app_user = session.get(AppUser, app_user_id)
    if app_user is None:
        return False

    session.delete(app_user)
    utils.commit(session)

    return True
