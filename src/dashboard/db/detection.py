"""CRUD helpers for the object_detection table"""

from typing import Any

from sqlalchemy import select, DateTime
from sqlalchemy.orm import Session

from .data_model import ObjectDetection
from . import utils


def add_object_detection(
    session: Session,
    *,
    image_capture_id: int,
    det_model_id: int,
    confidence: float,
    bbox: Any,
    detected_class: str,
    created_at: DateTime | None = None,
) -> ObjectDetection:
    """Insert a new object_detection row and return the persisted object."""

    object_detection = ObjectDetection(
        image_capture_id=image_capture_id,
        det_model_id=det_model_id,
        confidence=confidence,
        bbox=bbox,
        detected_class=detected_class,
    )

    if created_at is not None:
        object_detection.created_at = created_at

    session.add(object_detection)
    utils.commit(session)
    session.refresh(object_detection)

    return object_detection


def select_object_detections(session: Session) -> list[ObjectDetection]:
    """Return all object_detection rows ordered by primary key."""

    statement = select(ObjectDetection).order_by(ObjectDetection.id)
    return list(session.execute(statement).scalars().all())


def get_object_detection(
    session: Session, object_detection_id: int
) -> ObjectDetection | None:
    """Return one object_detection row by primary key."""

    return session.get(ObjectDetection, object_detection_id)


def get_object_detections_by_filter(
    session: Session, **filters: Any
) -> list[ObjectDetection]:
    """Return a list of object_detection rows filtered by the provided keyword arguments."""

    if not filters:
        raise ValueError(
            "At least one filter must be provided."
            "To select all detections, use `select_object_detections()` instead."
        )

    statement = (
        select(ObjectDetection).filter_by(**filters).order_by(ObjectDetection.id)
    )
    return list(session.execute(statement).scalars().all())


def update_object_detection(
    session: Session, object_detection_id: int, **changes: Any
) -> ObjectDetection | None:
    """Update an object_detection row and return the refreshed object, or None if missing."""

    object_detection = session.get(ObjectDetection, object_detection_id)
    if object_detection is None:
        return None

    if not changes:
        return object_detection

    allowed_fields = {
        "image_capture_id",
        "det_model_id",
        "confidence",
        "bbox",
        "detected_class",
    }
    unexpected_fields = set(changes.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(
            f"Unsupported object_detection fields: {sorted(unexpected_fields)}"
        )

    for key, value in changes.items():
        setattr(object_detection, key, value)

    utils.commit(session)
    session.refresh(object_detection)

    return object_detection


def delete_object_detection(session: Session, object_detection_id: int) -> bool:
    """Delete an object_detection row by primary key. Return True if deleted, False if not found."""

    object_detection = session.get(ObjectDetection, object_detection_id)
    if object_detection is None:
        return False

    session.delete(object_detection)
    utils.commit(session)

    return True
