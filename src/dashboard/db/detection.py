"""CRUD helpers for the object_detection table"""

from typing import Any

from sqlalchemy import select, DateTime
from sqlalchemy.orm import Session

from .data_model import ObjectDetection, DetectionCorrection
from dashboard.db.crud import CRUDBase
from . import utils


class ObjectDetectionCRUD(CRUDBase[ObjectDetection]):
    def __init__(self):
        """CRUD helper for the object_detection table."""
        super().__init__(ObjectDetection)

    def add_object_detection(
        self,
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

    def update(self, *args, **kwargs) -> Any:
        """This method is not intended to be used directly.
        Correction of a detection should be stored in DetectionCorrection table."""

        raise NotImplementedError(
            "Direct update of object_detection is not allowed. "
            "Use DetectionCorrectionCRUD to store corrections for object detections."
        )


class DetectionCorrectionCRUD(CRUDBase[DetectionCorrection]):
    def __init__(self):
        """CRUD helper for the detection_correction table."""
        super().__init__(DetectionCorrection)


# create instances of ObjectDetectionCRUD and DetectionCorrectionCRUD to be used in other modules
detection_crud = ObjectDetectionCRUD()
detection_correction_crud = DetectionCorrectionCRUD()
