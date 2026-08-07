"""CRUD helpers for the camera and camera_location_history tables"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .data_model import Camera, CameraLocationHistory
from dashboard.db.crud import CRUDBase
from . import utils
from datetime import datetime


# CRUD helpers for the camera table
class CameraCRUD(CRUDBase[Camera]):
    """CRUD helper for the camera table"""

    def __init__(self, location_history_crud: CameraLocationHistoryCRUD):
        super().__init__(Camera)
        self.location_history_crud = location_history_crud

    def add(
        self,
        session: Session,
        *,
        name: str,
        location: Any,
        description: str | None = None,
        installation_date: datetime | None = None,
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
        session.flush()  # get camera.id without committing

        # add an entry to the camera_location_history table
        self.location_history_crud.add_location_change(
            session,
            camera_id=camera.id,
            location=location,
            valid_from=camera.installation_date,
            commit=False,  # commit after both camera and history are added
            refresh=False,  # refresh after commit
        )

        utils.commit(session)
        session.refresh(camera)  # get generated fields like ID and installation_date

        return camera

    def update(self, session: Session, camera_id: int, **changes: Any) -> Camera | None:
        """Update a camera row and return the refreshed object, or None if missing."""

        camera = session.get(Camera, camera_id)
        if camera is None:
            return None

        allowed_fields = {
            "name",
            "location",
            "description",
            "installation_date",
            "status",
        }
        unexpected_fields = set(changes.keys()) - allowed_fields
        if unexpected_fields:
            raise ValueError(
                f"Unexpected fields for update: {unexpected_fields}. "
                f"Allowed fields are: {allowed_fields}."
            )

        if "location" in changes:
            new_location = utils.normalize_location(changes["location"])
            old_location = utils.location_to_text(session, Camera, camera_id)

            if new_location != old_location:
                # Add a new entry to the camera_location_history table for the new location
                self.location_history_crud.add_location_change(
                    session,
                    camera_id=camera_id,
                    location=changes["location"],
                    commit=False,
                    refresh=False,
                )

                changes["location"] = new_location
            else:
                # If the location hasn't changed, remove it from the changes to avoid unnecessary updates
                del changes["location"]

        return super().update(
            session,
            camera_id,
            allowed_fields=allowed_fields,
            **changes,
        )


# CRUD helpers for the camera_location_history table
class CameraLocationHistoryCRUD(CRUDBase[CameraLocationHistory]):
    """CRUD helper for the camera_location_history table"""

    def __init__(self):
        super().__init__(CameraLocationHistory)

    def add(self, *arg, **kwargs):
        """This method is not intended to be used directly.
        Use add_location_change() instead."""

        raise NotImplementedError(
            "Direct addition to camera_location_history is not allowed. "
            "Use add_location_change() to add a new location change."
        )

    def add_location_change(
        self,
        session: Session,
        *,
        camera_id: int,
        location: Any,
        valid_from: datetime | None = None,
        commit: bool = True,
        refresh: bool = True,
    ) -> CameraLocationHistory:
        """Insert a new camera_location_history row and return the persisted object.
        If the camera_id already has row(s) in the table,
        the valid_to of the most recent row will be updated to now() before inserting the new row.
        """

        new_history = CameraLocationHistory(
            camera_id=camera_id,
            location=utils.normalize_location(location),
            valid_to=None,
        )

        if valid_from is not None:
            new_history.valid_from = valid_from

        # update the most recent history's valid_to to now()
        # before adding the new history
        self.update_valid_to_most_recent_history(
            session, camera_id, commit=False, refresh=False
        )

        session.add(new_history)
        if commit:
            utils.commit(session)
        if refresh:
            session.refresh(new_history)  # get generated fields like ID

        return new_history

    def get_by_camera(
        self, session: Session, camera_id: int
    ) -> list[CameraLocationHistory]:
        """Return all camera_location_history rows for a given camera, ordered by valid_from."""

        statement = (
            select(CameraLocationHistory)
            .where(CameraLocationHistory.camera_id == camera_id)
            .order_by(CameraLocationHistory.valid_from.desc())
        )
        return list(session.execute(statement).scalars().all())

    def update(self, *arg, **kwargs):
        """This method is not intended to be used directly.
        Use add_location_change() instead."""

        raise NotImplementedError(
            "Direct updates to camera_location_history are not allowed. "
            "Use add_location_change() to add a new location change."
        )

    def update_valid_to_most_recent_history(
        self,
        session: Session,
        camera_id: int,
        commit: bool = True,
        refresh: bool = True,
    ) -> CameraLocationHistory | None:
        """Update the valid_to of the most recent camera_location_history row for a given camera,"""

        statement = (
            select(CameraLocationHistory)
            .where(CameraLocationHistory.camera_id == camera_id)
            .order_by(CameraLocationHistory.valid_from.desc())
            .limit(1)
        )

        recent_history = session.execute(statement).scalars().first()

        if recent_history is None:
            return None

        recent_history.valid_to = func.now()
        if commit:
            utils.commit(session)
        if refresh:
            session.refresh(recent_history)
        return recent_history

    def delete(self, *arg, **kwargs):
        """This method is not intended to be used directly.
        Use delete_old_camera_history() instead."""

        raise NotImplementedError(
            "Direct deletion of camera_location_history rows is not allowed. "
            "Use delete_old_camera_history() to remove old rows."
        )

    def delete_old_camera_history(self, session: Session, camera_id: int) -> bool:
        """Delete old camera_location_history rows for a given camera.
        Keep the most recent row (with valid_to = None) and delete all older rows.
        Returns True when rows were removed."""

        histories = self.get_by_camera(session, camera_id)

        if not histories:
            return False

        for history in histories:
            if history.valid_to is not None:
                session.delete(history)

        assert (
            len(self.get_by_camera(session, camera_id)) == 1
        )  # only the most recent row remains

        utils.commit(session)
        return True


# Create instances of the CRUD helpers for use in other modules
camera_location_history_crud = CameraLocationHistoryCRUD()
camera_crud = CameraCRUD(location_history_crud=camera_location_history_crud)
