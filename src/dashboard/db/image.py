"""CRUD helpers for the image table"""

from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .data_model import ImageCapture
from dashboard.db.crud import CRUDBase
from . import utils
from datetime import datetime


class ImageCRUD(CRUDBase[ImageCapture]):
    """CRUD helper for the image_capture table"""

    def __init__(self):
        super().__init__(ImageCapture)

    def add(
        self,
        session: Session,
        *,
        camera_id: int,
        image_path: str,
        location: Any,
        captured_at: datetime | None = None,
        uploaded_at: datetime | None = None,
        tobe_deleted: bool = False,
    ) -> ImageCapture:
        """Insert a new image_capture row and return the persisted object."""

        image_capture = ImageCapture(
            camera_id=camera_id,
            image_path=image_path,
            location=utils.normalize_location(location),
            tobe_deleted=tobe_deleted,
        )

        if captured_at is not None:
            image_capture.captured_at = captured_at
        if uploaded_at is not None:
            image_capture.uploaded_at = uploaded_at

        session.add(image_capture)
        utils.commit(session)
        session.refresh(
            image_capture
        )  # get generated fields like ID, default timestamps

        return image_capture

    def get_images_to_delete(self, session: Session) -> list[ImageCapture]:
        """Return a list of image_capture rows that are marked for deletion."""

        statement = select(ImageCapture).where(ImageCapture.tobe_deleted.is_(True))
        return list(session.execute(statement).scalars().all())

    def get_images_in_period(
        self, session: Session, start_time: datetime, end_time: datetime | None = None
    ) -> list[ImageCapture]:
        """Return a list of image_capture rows captured within the specified time period.
        If end_time is None, it will return images captured after start_time.
        start_time and end_time are inclusive.
        """

        if end_time is not None:
            statement = select(ImageCapture).where(
                ImageCapture.captured_at >= start_time,
                ImageCapture.captured_at <= end_time,
            )
        else:
            statement = select(ImageCapture).where(
                ImageCapture.captured_at >= start_time
            )

        return list(session.execute(statement).scalars().all())

    def update(self, *arg, **kwargs):
        """This method is not intended to be used directly.
        Use mark_image_for_deletion() instead."""

        raise NotImplementedError(
            "Direct update of image_capture rows is not allowed. "
            "Use mark_image_for_deletion() to mark an image for deletion."
        )

    def mark_image_for_deletion(self, session: Session, image_capture_id: int) -> bool:
        """Mark an image_capture row for deletion by setting the tobe_deleted flag to True.
        Returns True if the row was found and updated, False otherwise.
        """

        image_capture = session.get(ImageCapture, image_capture_id)
        if image_capture is None:
            return False

        image_capture.tobe_deleted = True
        utils.commit(session)
        session.refresh(image_capture)
        return True


# Create a single instance of ImageCRUD to be used later
image_crud = ImageCRUD()
