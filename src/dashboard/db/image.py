"""CRUD helpers for the image table"""

from typing import Any

from sqlalchemy import select, DateTime, func
from sqlalchemy.orm import Session

from .data_model import ImageCapture
from . import utils


def add_image_capture(
    session: Session,
    *,
    camera_id: int,
    image_path: str,
    location: Any,
    captured_at: DateTime | None = None,
    uploaded_at: DateTime | None = None,
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
    session.refresh(image_capture)  # get generated fields like ID, default timestamps

    return image_capture


def select_image_captures(session: Session) -> list[ImageCapture]:
    """Return all image_capture rows ordered by primary key."""

    statement = select(ImageCapture).order_by(ImageCapture.id)
    return list(session.execute(statement).scalars().all())


def get_image_capture(session: Session, image_capture_id: int) -> ImageCapture | None:
    """Return one image_capture row by primary key."""

    return session.get(ImageCapture, image_capture_id)


def get_images_by_filter(session: Session, **filters: Any) -> list[ImageCapture]:
    """Return a list of image_capture rows filtered by the provided keyword arguments."""

    if not filters:
        raise ValueError(
            "At least one filter must be provided."
            "To select all images, use `select_image_captures()` instead."
        )

    statement = select(ImageCapture).filter_by(**filters).order_by(ImageCapture.id)
    return list(session.execute(statement).scalars().all())


def get_images_to_delete(session: Session) -> list[ImageCapture]:
    """Return a list of image_capture rows that are marked for deletion."""

    statement = select(ImageCapture).where(ImageCapture.tobe_deleted.is_(True))
    return list(session.execute(statement).scalars().all())


def get_images_in_period(
    session: Session, start_time: DateTime, end_time: DateTime | None = None
) -> list[ImageCapture]:
    """Return a list of image_capture rows captured within the specified time period.
    If end_time is None, it will return images captured after start_time.
    start_time and end_time are inclusive.
    """

    if end_time is not None:
        statement = select(ImageCapture).where(
            ImageCapture.captured_at >= start_time, ImageCapture.captured_at <= end_time
        )
    else:
        statement = select(ImageCapture).where(ImageCapture.captured_at >= start_time)

    return list(session.execute(statement).scalars().all())


def mark_image_for_deletion(session: Session, image_capture_id: int) -> bool:
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


def delete_image_capture(session: Session, image_capture_id: int) -> bool:
    """Delete an image_capture row. Returns True when a row was removed."""

    image_capture = session.get(ImageCapture, image_capture_id)
    if image_capture is None:
        return False

    session.delete(image_capture)
    utils.commit(session)
    return True
