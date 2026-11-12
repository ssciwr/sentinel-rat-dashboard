"""CRUD helpers for the app_user table"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dashboard.db.crud import CRUDBase

from . import utils
from .data_model import AppUser


class AppUserCRUD(CRUDBase[AppUser]):
    """CRUD helper for the app_user table.

    Password hashing (from plaintext to an encrypted form) happens in R before this function is called
    This function is used to communicate between the SQL DB and the R app through python

    For example set password updates the hashed(encrypted) password in the SQL database based on the
    existing property for that for the AppUser model.
    """

    def __init__(self):
        super().__init__(AppUser)

    def add(
        self,
        session: Session,
        *,
        username: str,
        password: str,
        full_name: str | None = None,
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> AppUser:
        """Insert a new app_user row and return the persisted object.
        password must already be hashed or encrypted, never plain text.
        """

        app_user = AppUser(
            username=username,
            password=password,
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

        allowed_fields = {"full_name", "password", "is_active"}
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

    def get_login(
        self, session: Session, username: str
    ) -> dict[str, str | int | bool | None] | None:
        statement = select(
            AppUser.id.label("app_user_id"),
            AppUser.username.label("user"),
            func.nullif(AppUser.password, "").label("password"),
            AppUser.is_active,
        ).where(AppUser.username == username)
        row = session.execute(statement).mappings().one_or_none()
        return dict(row) if row is not None else None

    def set_password(
        self,
        session: Session,
        *,
        username: str,
        password: str,
    ) -> AppUser:
        if not username.strip() or len(username) > 50:
            raise ValueError("Username must contain 1 to 50 characters.")
        user = session.scalar(select(AppUser).where(AppUser.username == username))
        if user is None:
            return self.add(
                session,
                username=username,
                password=password,
            )
        updated = self.update(session, user.id, password=password)
        if updated is None:
            raise ValueError("User no longer exists.")
        return updated


# create an instance of the AppUserCRUD class to be used in other modules
app_user_crud = AppUserCRUD()
