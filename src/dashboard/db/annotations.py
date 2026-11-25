from math import isfinite
from typing import Literal, TypedDict

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .analysis_result import daily_analysis_result_crud
from .data_model import (
    AppUser,
    ClassificationCorrection,
    DetectionCorrection,
    ImageCapture,
    MLModel,
    ObjectDetection,
    Taxonomy,
)
from .detection import detection_crud

AnnotationEvent = Literal[
    "bbox_created", "bbox_edited", "bbox_deleted", "species_changed"
]

"""
Store corrections in the code without modifying the original camera detection/classification outputs.
"""


class AnnotationSave(TypedDict):
    target_id: str
    analysis_warning: bool


def _annotation_bbox(coordinates: dict[str, float]) -> dict[str, float]:

    x0, y0, x1, y1 = (coordinates[key] for key in ("x0", "y0", "x1", "y1"))
    if not all(isfinite(value) for value in (x0, y0, x1, y1)):
        raise ValueError("Box coordinates must be finite.")
    if x0 < 0 or y0 < 0 or x1 <= x0 or y1 <= y0:
        raise ValueError("A box must have positive dimensions inside the image.")
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}


def _save_species(
    session: Session,
    correction: DetectionCorrection,
    detection: ObjectDetection | None,
    species: str,
) -> None:
    taxonomy = session.scalar(
        select(Taxonomy).where(
            or_(
                Taxonomy.species == species,
                func.trim(Taxonomy.genus + " " + func.coalesce(Taxonomy.species, ""))
                == species,
            )
        )
    )
    if taxonomy is None:
        raise ValueError("Choose a species from the database.")
    classification = detection_crud.top_classification(detection) if detection else None
    if detection is not None and classification is None:
        raise ValueError("This detection has no species classification to correct.")
    target = {
        "species_classification_id": classification.id if classification else None,
        "new_obj_det_id": correction.new_detection_id,
        "app_user_id": correction.app_user_id,
    }
    species_correction = session.scalar(
        select(ClassificationCorrection).filter_by(**target)
    )
    if species_correction is None:
        species_correction = ClassificationCorrection(
            **target,
            action="update" if detection else "add",
        )
        if detection is not None:
            species_correction.new_classification_id = None
        session.add(species_correction)
    species_correction.corrected_taxonomy_id = taxonomy.id
    species_correction.last_updated = func.now()


def _annotation_target(
    session: Session,
    image_capture_id: int,
    app_user_id: int,
    detection_id: str,
    event_type: AnnotationEvent,
) -> tuple[DetectionCorrection, ObjectDetection | None]:
    # Check if according to this detection-correction system there is already a correction record
    if detection_id.startswith("added-"):
        correction = session.scalar(
            select(DetectionCorrection).filter_by(
                new_detection_id=int(detection_id[6:]),
                image_capture_id=image_capture_id,
            )
        )
        if correction is None:
            raise ValueError("The added detection does not belong to this image.")
        correction.app_user_id = app_user_id
        return correction, None

    detection = None
    if event_type != "bbox_created":
        detection = session.get(ObjectDetection, int(detection_id))
        if detection is None or detection.image_capture_id != image_capture_id:
            raise ValueError("The detection does not belong to this image.")
        correction = session.scalar(
            select(DetectionCorrection).filter_by(
                object_detection_id=detection.id, app_user_id=app_user_id
            )
        )
        if correction is not None:
            return correction, detection
        model_id = detection.det_model_id
    else:
        # Keep an added animal with the frame's detection model in daily counts.
        model_id = session.scalar(
            select(ObjectDetection.det_model_id)
            .where(ObjectDetection.image_capture_id == image_capture_id)
            .order_by(ObjectDetection.id)
        )
        if model_id is None:
            model_id = session.scalar(
                select(MLModel.id)
                .where(MLModel.task == "detection")
                .order_by(MLModel.id)
            )
    if model_id is None:
        raise ValueError("No detection model is available for this image.")
    correction = DetectionCorrection(
        object_detection_id=detection.id if detection else None,
        image_capture_id=image_capture_id,
        det_model_id=model_id,
        app_user_id=app_user_id,
        corrected_class=detection.detected_class if detection else "animal",
    )
    if detection is not None:
        correction.new_detection_id = None
    session.add(correction)
    return correction, detection


def save_annotation(
    session: Session,
    *,
    app_user_id: int,
    image_capture_id: int,
    detection_id: str,
    event_type: AnnotationEvent,
    bbox: dict[str, float] | None = None,
    species: str = "",
) -> AnnotationSave:
    if event_type not in (
        "bbox_created",
        "bbox_edited",
        "bbox_deleted",
        "species_changed",
    ):
        raise ValueError("Unsupported annotation event.")
    account = session.get(AppUser, app_user_id)
    if account is None or not account.is_active:
        raise ValueError("An active reviewer is required.")
    image = session.get(ImageCapture, image_capture_id, with_for_update=True)
    if image is None:
        raise ValueError("The image no longer exists.")

    with session.begin_nested():
        correction, detection = _annotation_target(
            session, image.id, app_user_id, detection_id, event_type
        )
        if bbox is not None:
            correction.corrected_bbox = _annotation_bbox(bbox)
        elif correction.corrected_bbox is None and detection is not None:
            correction.corrected_bbox = detection.bbox
        if correction.corrected_bbox is None:
            raise ValueError("A bounding box is required.")
        correction.action = "remove" if event_type == "bbox_deleted" else "update"
        if detection is None and event_type != "bbox_deleted":
            correction.action = "add"
        correction.last_updated = func.now()
        session.flush()
        if event_type == "species_changed" or (
            detection is None and event_type != "bbox_deleted"
        ):
            _save_species(session, correction, detection, species)

    warning = daily_analysis_result_crud.commit_with_recompute(session, image.id)
    target_id = (
        str(detection.id) if detection else f"added-{correction.new_detection_id}"
    )
    return {"target_id": target_id, "analysis_warning": warning is not None}
