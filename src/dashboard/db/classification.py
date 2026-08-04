"""CRUD helpers for the species_classification table"""

from typing import Any

from sqlalchemy import select, DateTime
from sqlalchemy.orm import Session

from .data_model import SpeciesClassification
from . import utils


def add_species_classification(
    session: Session,
    *,
    object_detection_id: int,
    taxonomy_id: int,
    clas_model_id: int,
    confidence: float,
    created_at: DateTime | None = None,
) -> SpeciesClassification:
    """Insert a new species_classification row and return the persisted object."""

    species_classification = SpeciesClassification(
        object_detection_id=object_detection_id,
        taxonomy_id=taxonomy_id,
        clas_model_id=clas_model_id,
        confidence=confidence,
    )

    if created_at is not None:
        species_classification.created_at = created_at

    session.add(species_classification)
    utils.commit(session)
    session.refresh(species_classification)

    return species_classification


def select_species_classifications(session: Session) -> list[SpeciesClassification]:
    """Return all species_classification rows ordered by primary key."""

    statement = select(SpeciesClassification).order_by(SpeciesClassification.id)
    return list(session.execute(statement).scalars().all())


def get_species_classification(
    session: Session, species_classification_id: int
) -> SpeciesClassification | None:
    """Return one species_classification row by primary key."""

    return session.get(SpeciesClassification, species_classification_id)


def get_species_classifications_by_filter(
    session: Session, **filters: Any
) -> list[SpeciesClassification]:
    """Return a list of species_classification rows filtered by the provided keyword arguments."""

    if not filters:
        raise ValueError(
            "At least one filter must be provided."
            "To select all classifications, use `select_species_classifications()` instead."
        )

    statement = (
        select(SpeciesClassification)
        .filter_by(**filters)
        .order_by(SpeciesClassification.id)
    )
    return list(session.execute(statement).scalars().all())


def update_species_classification(
    session: Session, species_classification_id: int, **changes: Any
) -> SpeciesClassification | None:
    """Update a species_classification row and return the refreshed object, or None if missing."""

    species_classification = session.get(
        SpeciesClassification, species_classification_id
    )
    if species_classification is None:
        return None

    if not changes:
        return species_classification

    allowed_fields = {
        "confidence",
    }
    unexpected_fields = set(changes.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(
            f"Unsupported species_classification fields: {sorted(unexpected_fields)}"
        )

    for key, value in changes.items():
        setattr(species_classification, key, value)

    utils.commit(session)
    session.refresh(species_classification)

    return species_classification


def delete_species_classification(
    session: Session, species_classification_id: int
) -> bool:
    """Delete a species_classification row by primary key. Return True if deleted, False if not found."""

    species_classification = session.get(
        SpeciesClassification, species_classification_id
    )
    if species_classification is None:
        return False

    session.delete(species_classification)
    utils.commit(session)

    return True
