"""CRUD helpers for the camera and camera_location_history tables"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, DateTime, func
from sqlalchemy.orm import Session

from .data_model import Camera, CameraLocationHistory
from . import utils


# CRUD helpers for the camera table
def add_camera(
    session: Session,
    *,
    name: str,
    location: Any,
    description: str | None = None,
    installation_date: DateTime | None = None,
    status: str = "active",
) -> Camera:
    """Insert a new camera row and return the persisted object."""

    camera = Camera(
        name=name,
        location=utils.normalize_location(location),
        description=description,
        status=status,
    )

    if installation_date is not None:
        camera.installation_date = installation_date

    session.add(camera)
    utils.commit(session)
    session.refresh(camera)  # get generated fields like ID and installation_date

    # update the camera_location_history table with the initial location
    add_camera_location_history(session, camera.id, location, camera.installation_date)

    return camera


def select_cameras(session: Session) -> list[Camera]:
    """Return all camera rows ordered by primary key."""

    statement = select(Camera).order_by(Camera.id)
    return list(session.execute(statement).scalars().all())


def get_camera(session: Session, camera_id: int) -> Camera | None:
    """Return one camera row by primary key."""

    return session.get(Camera, camera_id)


def update_camera(session: Session, camera_id: int, **changes: Any) -> Camera | None:
    """Update a camera row and return the refreshed object, or None if missing."""

    camera = session.get(Camera, camera_id)
    if camera is None:
        return None

    if not changes:
        return camera

    allowed_fields = {"name", "location", "description", "installation_date", "status"}
    unexpected_fields = set(changes.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"Unsupported camera fields: {sorted(unexpected_fields)}")

    if "location" in changes:
        new_location = utils.normalize_location(changes["location"])

        if new_location != camera.location:
            # Update the camera_location_history table if the location has changed
            update_camera_location_history(session, camera_id, new_location)

            changes["location"] = new_location

    for field_name, value in changes.items():
        setattr(camera, field_name, value)

    utils.commit(session)
    session.refresh(camera)
    return camera


def delete_camera(session: Session, camera_id: int) -> bool:
    """Delete a camera row. Returns True when a row was removed."""

    camera = session.get(Camera, camera_id)
    if camera is None:
        return False

    session.delete(camera)
    utils.commit(session)
    return True


# CRUD helpers for the camera_location_history table
def add_camera_location_history(
    session: Session, camera_id: int, location: Any, valid_from: DateTime | None = None
) -> CameraLocationHistory:
    """Insert a new camera_location_history row and return the persisted object."""

    history = CameraLocationHistory(
        camera_id=camera_id,
        location=utils.normalize_location(location),
        valid_to=None,
    )

    if valid_from is not None:
        history.valid_from = valid_from

    session.add(history)
    utils.commit(session)
    session.refresh(history)
    return history


def get_camera_location_history(
    session: Session, camera_id: int
) -> list[CameraLocationHistory]:
    """Return all camera_location_history rows for a given camera, ordered by valid_from."""

    statement = (
        select(CameraLocationHistory)
        .filter(CameraLocationHistory.camera_id == camera_id)
        .order_by(CameraLocationHistory.valid_from)
    )
    return list(session.execute(statement).scalars().all())


def update_camera_location_history(
    session: Session, camera_id: int, new_location: Any
) -> CameraLocationHistory | None:
    """Update the camera_location_history table when a camera's location changes."""

    # Get the current location history for this camera
    current_history = (
        session.query(CameraLocationHistory)
        .filter(CameraLocationHistory.camera_id == camera_id)
        .order_by(CameraLocationHistory.valid_from.desc())
        .first()
    )

    new_location_str = utils.normalize_location(new_location)

    if current_history is not None:
        # If the location hasn't changed, do nothing
        if current_history.location == new_location_str:
            return current_history

        # Update the valid_to of the current history entry
        current_history.valid_to = func.now()

    # Insert a new history entry for the new location
    new_history = CameraLocationHistory(
        camera_id=camera_id,
        location=new_location_str,
        valid_from=func.now(),
        valid_to=None,
    )
    session.add(new_history)
    utils.commit(session)
    session.refresh(new_history)
    return new_history


def delete_camera_location_history(session: Session, camera_id: int) -> bool:
    """Delete all camera_location_history rows for a given camera. Returns True when rows were removed."""

    histories = (
        session.query(CameraLocationHistory)
        .filter(CameraLocationHistory.camera_id == camera_id)
        .all()
    )

    if not histories:
        return False

    for history in histories:
        session.delete(history)

    utils.commit(session)
    return True
