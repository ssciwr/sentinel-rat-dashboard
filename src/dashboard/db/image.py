"""CRUD helpers for the image table"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from dashboard.db.crud import CRUDBase

from . import utils
from .data_model import ImageCapture


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
    ) -> ImageCapture:
        """Insert a new image_capture row and return the persisted object.
        New images are not analyzed yet and are in the watch folder.
        """

        image_capture = ImageCapture(
            camera_id=camera_id,
            image_path=image_path,
            location=utils.normalize_location(location),
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

    def get_images_to_move(self, session: Session) -> list[ImageCapture]:
        """Return a list of image_capture rows that are analyzed
        and still in the watch folder, i.e. ready to be moved out.
        """

        statement = select(ImageCapture).where(
            ImageCapture.analyzed_at.is_not(None),
            ImageCapture.file_status == "in_watch_folder",
        )
        return list(session.execute(statement).scalars().all())

    def get_images_by_file_status(
        self, session: Session, file_status: str
    ) -> list[ImageCapture]:
        """Return a list of image_capture rows with the given file_status
        (in_watch_folder, moved or missing).
        """

        statement = select(ImageCapture).where(ImageCapture.file_status == file_status)
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
        Use mark_image_as_analyzed(), mark_image_as_moved(),
        mark_image_as_missing() or mark_image_as_restored() instead."""

        raise NotImplementedError(
            "Direct update of image_capture rows is not allowed. "
            "Use mark_image_as_analyzed() to mark an image as analyzed, "
            "mark_image_as_moved() to mark an image as moved out of the watch folder, "
            "mark_image_as_missing() to mark an image as missing "
            "or mark_image_as_restored() to mark a missing image as back in the watch folder."
        )

    def mark_image_as_analyzed(self, session: Session, image_capture_id: int) -> bool:
        """Mark an image_capture row as used for daily analysis by setting analyzed_at.
        Returns True if the row was found and updated, False otherwise.
        """

        image_capture = session.get(ImageCapture, image_capture_id)
        if image_capture is None:
            return False

        image_capture.analyzed_at = datetime.now(UTC)
        utils.commit(session)
        session.refresh(image_capture)
        return True

    def mark_image_as_moved(self, session: Session, image_capture_id: int) -> bool:
        """Mark an image_capture row as moved out of the watch folder.
        Returns True if the row was found and updated, False otherwise.
        Raises ValueError if the image is not analyzed or not in the watch folder.
        """

        image_capture = session.get(ImageCapture, image_capture_id)
        if image_capture is None:
            return False
        if image_capture.analyzed_at is None:
            raise ValueError("An image can only be moved once it is analyzed.")
        if image_capture.file_status != "in_watch_folder":
            raise ValueError(
                f"Image is {image_capture.file_status}, "
                "only images in the watch folder can be moved."
            )

        self._change_file_status(session, image_capture, "moved")
        return True

    def mark_image_as_missing(self, session: Session, image_capture_id: int) -> bool:
        """Mark an image_capture row as missing, i.e. gone from the watch folder
        without being moved by the service. analyzed_at is kept as is.
        Returns True if the row was found and updated, False otherwise.
        Raises ValueError if the image is not in the watch folder.
        """

        image_capture = session.get(ImageCapture, image_capture_id)
        if image_capture is None:
            return False
        if image_capture.file_status != "in_watch_folder":
            raise ValueError(
                f"Image is {image_capture.file_status}, "
                "only images in the watch folder can be marked as missing."
            )

        self._change_file_status(session, image_capture, "missing")
        return True

    def mark_image_as_restored(self, session: Session, image_capture_id: int) -> bool:
        """Mark a missing image_capture row as back in the watch folder,
        e.g. when the file is copied back manually. analyzed_at is kept as is.
        Returns True if the row was found and updated, False otherwise.
        Raises ValueError if the image is not missing.
        """

        image_capture = session.get(ImageCapture, image_capture_id)
        if image_capture is None:
            return False
        if image_capture.file_status != "missing":
            raise ValueError(
                f"Image is {image_capture.file_status}, "
                "only missing images can be restored."
            )

        self._change_file_status(session, image_capture, "in_watch_folder")
        return True

    def _change_file_status(
        self, session: Session, image_capture: ImageCapture, file_status: str
    ) -> None:
        """Set file_status and persist the change."""

        image_capture.file_status = file_status
        utils.commit(session)
        session.refresh(image_capture)


# Create a single instance of ImageCRUD to be used later
image_crud = ImageCRUD()
