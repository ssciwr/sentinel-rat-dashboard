from __future__ import annotations
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func

CRS = 4326
STR_POINT = "SRID={};POINT({} {})"


def normalize_location(location: Any) -> str:
    """Convert a location to a string in the format 'SRID=4326;POINT(lon lat)'."""

    if isinstance(location, str) and location.startswith("SRID="):
        return location

    try:
        lon, lat = location
    except Exception:
        raise ValueError(
            f"Invalid location: {location}. Must be a string or a (lon, lat) tuple."
        )

    return STR_POINT.format(CRS, lon, lat)


def location_to_text(session, table, row_id):
    statement = select(func.ST_AsText(table.location)).where(table.id == row_id)
    return session.execute(statement).scalar_one()


def commit(session: Session) -> None:
    """Commit the session, rolling back on error."""
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
