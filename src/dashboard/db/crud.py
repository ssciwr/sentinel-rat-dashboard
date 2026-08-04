from __future__ import annotations

from typing import TypeVar, Generic, Any, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from dashboard.db.database import Base
from . import utils

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):

    def __init__(self, model: type[ModelType]):
        """CRUD helper for a specific SQLAlchemy model class."""

        if not issubclass(model, Base):
            raise TypeError(f"{model} is not a subclass of Base")
        self.model = model

    def add(
        self,
        session: Session,
        *,
        commit: bool = True,
        refresh: bool = True,
        **create_kwargs: Any,
    ) -> ModelType:
        """Insert a new row and return the persisted object."""

        instance = self.model(**create_kwargs)
        session.add(instance)
        if commit:
            utils.commit(session)
        if refresh:
            session.refresh(instance)
        return instance

    def select(self, session: Session) -> list[ModelType]:
        """Return all rows ordered by primary key."""

        statement = select(self.model).order_by(self.model.id)
        return list(session.execute(statement).scalars().all())

    def get(self, session: Session, id: int) -> ModelType | None:
        """Return one row by primary key."""

        return session.get(self.model, id)

    def filter(self, session: Session, **filters: Any) -> list[ModelType]:
        """Return rows filtered by keyword arguments."""

        if not filters:
            raise ValueError(
                "At least one filter must be provided."
                f" To select all {self.model.__tablename__}, use `select()` instead."
            )

        statement = select(self.model).filter_by(**filters).order_by(self.model.id)
        return list(session.execute(statement).scalars().all())

    def update(
        self,
        session: Session,
        id: int,
        *,
        allowed_fields: Set[str] | None = None,
        **changes: Any,
    ) -> ModelType | None:
        """Update a row and return the refreshed object, or None if missing."""

        instance = session.get(self.model, id)
        if instance is None:
            return None
        if not changes:
            return instance

        if allowed_fields is not None:
            unexpected_fields = set(changes.keys()) - allowed_fields
            if unexpected_fields:
                raise ValueError(
                    f"Unsupported {self.model.__tablename__} fields: {sorted(unexpected_fields)}"
                )

        for key, value in changes.items():
            setattr(instance, key, value)

        utils.commit(session)
        session.refresh(instance)
        return instance

    def delete(self, session: Session, id: int) -> bool:
        """Delete a row by primary key. Return True if deleted."""

        instance = session.get(self.model, id)
        if instance is None:
            return False
        session.delete(instance)
        utils.commit(session)
        return True
