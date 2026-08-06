"""CRUD helpers for the app_user table"""

from typing import Any

from sqlalchemy import select, DateTime, func
from sqlalchemy.orm import Session

from .data_model import AppUser
from dashboard.db.crud import CRUDBase
from . import utils


class AppUserCRUD(CRUDBase[AppUser]):
    """CRUD helper for the app_user table."""

    def __init__(self):
        super().__init__(AppUser)

    def add(
        self,
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

    def update(
        self, session: Session, app_user_id: int, **changes: Any
    ) -> AppUser | None:
        """Update an app_user row and return the refreshed object, or None if missing."""

        app_user = session.get(AppUser, app_user_id)
        if app_user is None:
            return None

        allowed_fields = {"full_name", "is_active"}
        unexpected_fields = set(changes.keys()) - allowed_fields
        if unexpected_fields:
            raise ValueError(
                f"Unsupported app_user fields: {sorted(unexpected_fields)}"
            )

        # update the updated_at field to the current timestamp
        changes["updated_at"] = func.now()
        allowed_fields.add("updated_at")

        return super().update(
            session, app_user_id, allowed_fields=allowed_fields, **changes
        )


# create an instance of the AppUserCRUD class to be used in other modules
app_user_crud = AppUserCRUD()
