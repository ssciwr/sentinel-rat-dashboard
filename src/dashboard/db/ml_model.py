"""CRUD helpers for the ml_model table"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .data_model import MLModel
from . import utils


def add_ml_model(
    session: Session,
    *,
    name: str,
    task: str,
    version: str | None = None,
    description: str | None = None,
) -> MLModel:
    """Insert a new ml_model row and return the persisted object."""

    ml_model = MLModel(name=name, task=task)

    if version is not None:
        ml_model.version = version

    if description is not None:
        ml_model.description = description

    session.add(ml_model)
    utils.commit(session)
    session.refresh(ml_model)  # get generated fields like ID

    return ml_model


def select_ml_models(session: Session) -> list[MLModel]:
    """Return all ml_model rows ordered by primary key."""

    statement = select(MLModel).order_by(MLModel.id)
    return list(session.execute(statement).scalars().all())


def get_ml_model(session: Session, ml_model_id: int) -> MLModel | None:
    """Return one ml_model row by primary key."""

    return session.get(MLModel, ml_model_id)


def get_ml_models_by_filter(session: Session, **filters: Any) -> list[MLModel]:
    """Return a list of ml_model rows filtered by the provided keyword arguments."""

    if not filters:
        raise ValueError(
            "At least one filter must be provided."
            "To get all rows, use select_ml_models() instead."
        )

    statement = select(MLModel).filter_by(**filters).order_by(MLModel.id)
    return list(session.execute(statement).scalars().all())


def update_ml_model(
    session: Session, ml_model_id: int, **changes: Any
) -> MLModel | None:
    """Update a ml_model row and return the refreshed object, or None if missing."""

    ml_model = session.get(MLModel, ml_model_id)
    if ml_model is None:
        return None

    if not changes:
        return ml_model

    allowed_fields = {"name", "task", "version", "description"}
    unexpected_fields = set(changes.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"Unsupported ml_model fields: {sorted(unexpected_fields)}")

    for key, value in changes.items():
        setattr(ml_model, key, value)

    utils.commit(session)
    session.refresh(ml_model)

    return ml_model


def delete_ml_model(session: Session, ml_model_id: int) -> bool:
    """Delete a ml_model row by primary key. Return True if deleted, False if not found."""

    ml_model = session.get(MLModel, ml_model_id)
    if ml_model is None:
        return False

    session.delete(ml_model)
    utils.commit(session)

    return True
