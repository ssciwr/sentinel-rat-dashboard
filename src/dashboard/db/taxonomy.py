"""CRUD helpers for the taxonomy table"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .data_model import Taxonomy
from . import utils


def add_taxonomy(
    session: Session,
    *,
    species: str,
    kingdom: str | None = None,
    phylum: str | None = None,
    class_name: str | None = None,
    order: str | None = None,
    family: str | None = None,
    genus: str | None = None,
    common_name: str | None = None,
) -> Taxonomy:
    """Insert a new taxonomy row and return the persisted object."""

    taxonomy = Taxonomy(
        species=species,
        kingdom=kingdom,
        phylum=phylum,
        class_name=class_name,
        order=order,
        family=family,
        genus=genus,
        common_name=common_name,
    )

    session.add(taxonomy)
    utils.commit(session)
    session.refresh(taxonomy)

    return taxonomy


def select_taxonomies(session: Session) -> list[Taxonomy]:
    """Return all taxonomy rows ordered by primary key."""

    statement = select(Taxonomy).order_by(Taxonomy.id)
    return list(session.execute(statement).scalars().all())


def get_taxonomy(session: Session, taxonomy_id: int) -> Taxonomy | None:
    """Return one taxonomy row by primary key."""

    return session.get(Taxonomy, taxonomy_id)


def get_taxonomies_by_filter(session: Session, **filters: Any) -> list[Taxonomy]:
    """Return a list of taxonomy rows filtered by the provided keyword arguments."""

    if not filters:
        raise ValueError(
            "At least one filter must be provided."
            "To select all taxonomies, use `select_taxonomies()` instead."
        )

    statement = select(Taxonomy).filter_by(**filters).order_by(Taxonomy.id)
    return list(session.execute(statement).scalars().all())


def update_taxonomy(
    session: Session, taxonomy_id: int, **changes: Any
) -> Taxonomy | None:
    """Update a taxonomy row and return the refreshed object, or None if missing."""

    taxonomy = session.get(Taxonomy, taxonomy_id)
    if taxonomy is None:
        return None

    if not changes:
        return taxonomy

    allowed_fields = {
        "species",
        "kingdom",
        "phylum",
        "class_name",
        "order",
        "family",
        "genus",
        "common_name",
    }
    unexpected_fields = set(changes.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"Unsupported taxonomy fields: {sorted(unexpected_fields)}")

    for key, value in changes.items():
        setattr(taxonomy, key, value)

    utils.commit(session)
    session.refresh(taxonomy)

    return taxonomy


def delete_taxonomy(session: Session, taxonomy_id: int) -> bool:
    """Delete a taxonomy row by primary key. Return True if deleted, False if not found."""

    taxonomy = session.get(Taxonomy, taxonomy_id)
    if taxonomy is None:
        return False

    session.delete(taxonomy)
    utils.commit(session)

    return True
