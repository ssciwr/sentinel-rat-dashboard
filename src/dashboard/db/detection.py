"""CRUD helpers for the object_detection table"""

from typing import Any, Literal

from sqlalchemy import select, func, Sequence
from sqlalchemy.orm import Session

from .data_model import ObjectDetection, DetectionCorrection
from dashboard.db.crud import CRUDBase
from . import utils

from datetime import datetime


class ObjectDetectionCRUD(CRUDBase[ObjectDetection]):
    def __init__(self):
        """CRUD helper for the object_detection table."""
        super().__init__(ObjectDetection)

    def add(
        self,
        session: Session,
        *,
        image_capture_id: int,
        det_model_id: int,
        confidence: float,
        bbox: Any,
        detected_class: str,
        created_at: datetime | None = None,
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

    def update(self, *args, **kwargs) -> Any:
        """This method is not intended to be used directly.
        Correction of a detection should be stored in DetectionCorrection table."""

        raise NotImplementedError(
            "Direct update of object_detection is not allowed. "
            "Use DetectionCorrectionCRUD to store corrections for object detections."
        )


class DetectionCorrectionCRUD(CRUDBase[DetectionCorrection]):
    """CRUD helper for the detection_correction table."""

    def __init__(self):
        super().__init__(DetectionCorrection)

    def add(
        self,
        session: Session,
        *,
        object_detection_id: int | None,
        image_capture_id: int,
        det_model_id: int,
        app_user_id: int,
        corrected_bbox: Any,
        corrected_class: str,
        comment: str | None = None,
        last_updated: datetime | None = None,
        action: Literal["add", "update", "remove"] = "update",
    ) -> DetectionCorrection:
        """Insert a new detection_correction row and return the persisted object."""

        detection_correction = DetectionCorrection(
            object_detection_id=object_detection_id,
            image_capture_id=image_capture_id,
            det_model_id=det_model_id,
            app_user_id=app_user_id,
            corrected_bbox=corrected_bbox,
            corrected_class=corrected_class,
            comment=comment,
            action=action,
        )

        # 1. when action is "update" or "remove", object_detection_id must be provided
        # and new_detection_id will be None
        # 2. when action is "add", object_detection_id is None
        # new_detection_id is the next sequence value of new detections across rows
        # 3. otherwise, raise an error
        if object_detection_id is not None and action != "add":
            # no new detection is added
            detection_correction.new_detection_id = None
        elif object_detection_id is None and action != "add":
            raise ValueError(
                "object_detection_id must be provided unless action is 'add'."
            )
        elif object_detection_id is not None and action == "add":
            raise ValueError("object_detection_id must be None when action is 'add'.")
        else:
            # action is "add" and object_detection_id is None
            # get the next sequence value for new_detection_id
            detection_seq = Sequence("new_detection_id_seq")
            next_new_detection_id = session.scalar(select(detection_seq.next_value()))
            detection_correction.new_detection_id = next_new_detection_id

        if last_updated is not None:
            detection_correction.last_updated = last_updated

        session.add(detection_correction)
        utils.commit(session)
        session.refresh(detection_correction)

        return detection_correction

    def update(
        self, session: Session, detection_correction_id: int, **changes: Any
    ) -> DetectionCorrection | None:
        """Update a detection_correction row and return the refreshed object, or None if missing."""

        detection_correction = session.get(DetectionCorrection, detection_correction_id)
        if detection_correction is None:
            return None

        non_pk_fk_fields = {
            col.name
            for col in DetectionCorrection.__table__.columns
            if not col.primary_key and not col.foreign_keys
        }

        allowed_fields = non_pk_fk_fields - {
            "new_detection_id",
            "last_updated",
        }
        unexpected_fields = set(changes.keys()) - allowed_fields
        if unexpected_fields:
            raise ValueError(
                f"Unsupported detection_correction fields: {sorted(unexpected_fields)}"
            )

        # raise error if action is updated to "add"
        if "action" in changes and changes["action"] == "add":
            raise ValueError(
                "Direct update of action to 'add' is not allowed. "
                "Use the add() method to create a new detection correction."
            )

        # update last_updated to current timestamp
        detection_correction.last_updated = func.now()

        return super().update(
            session, detection_correction_id, allowed_fields=allowed_fields, **changes
        )


# create instances of ObjectDetectionCRUD and DetectionCorrectionCRUD to be used in other modules
detection_crud = ObjectDetectionCRUD()
detection_correction_crud = DetectionCorrectionCRUD()
