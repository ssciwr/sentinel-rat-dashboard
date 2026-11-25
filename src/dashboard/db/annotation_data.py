"""Read real image records and their corrected detections for the editor."""

from datetime import date
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .analysis_result import (
    _added_detection_species,
    _detection_species,
    _latest,
    day_bounds,
)
from .data_model import (
    DetectionCorrection,
    ImageCapture,
    ObjectDetection,
    SpeciesClassification,
    Taxonomy,
)


class AnnotationData(TypedDict):
    images: list[dict[str, str | int | float | None]]
    detections: list[dict[str, str | float]]


def _species_label(taxonomy: Taxonomy) -> str:
    # Convert between the data selector and our backend loaded DB data
    species = taxonomy.species or ""
    if species.startswith(taxonomy.genus + " "):
        return species
    return f"{taxonomy.genus} {species}".strip()


def _image_detections(
    image: ImageCapture, taxonomies: dict[int, str]
) -> list[dict[str, str | float]]:
    detections = []
    for detection in image.object_detections:
        species = _detection_species(detection, 0, 0)
        if species is not None:
            correction = _latest(detection.detection_corrections)
            detections.append((str(detection.id), correction or detection, species))
    for correction in image.detection_corrections:
        if correction.object_detection_id is not None:
            continue
        species = _added_detection_species(correction)
        if species is not None:
            detections.append(
                (f"added-{correction.new_detection_id}", correction, species)
            )

    detection_rows = []
    for detection_id, source, (taxonomy_id, confidence) in detections:
        corrected = isinstance(source, DetectionCorrection)
        bbox = source.corrected_bbox if corrected else source.bbox
        label = taxonomies[taxonomy_id]
        detection_rows.append(
            {
                "detection_id": detection_id,
                "image_id": str(image.id),
                "label": label,
                "genus_detected": label.split()[0],
                "confidence": confidence,
                "origin_type": "human" if corrected else "machine",
                "origin_name": source.user.username
                if corrected
                else source.ml_model.name,
                "x": bbox["x"],
                "y": bbox["y"],
                "width": bbox["width"],
                "height": bbox["height"],
            }
        )
    return detection_rows


def load_annotation_data(session: Session, camera_id: int, day: str) -> AnnotationData:
    # Get the image and detection annotations (bbox + class) for a given day
    start, end = day_bounds(date.fromisoformat(day)) # Match DB format, no real better R type for this without extra boilerplate
    taxonomies = {
        taxonomy.id: _species_label(taxonomy)
        for taxonomy in session.scalars(select(Taxonomy))
    }
    images = session.scalars(
        select(ImageCapture)
        .where(
            ImageCapture.camera_id == camera_id,
            ImageCapture.captured_at >= start,
            ImageCapture.captured_at < end,
        )
        .options(
            selectinload(ImageCapture.object_detections).selectinload(
                ObjectDetection.detection_corrections
            ),
            selectinload(ImageCapture.object_detections)
            .selectinload(ObjectDetection.species_classifications)
            .selectinload(SpeciesClassification.classification_corrections),
            selectinload(ImageCapture.detection_corrections).selectinload(
                DetectionCorrection.classification_corrections
            ),
        )
        .order_by(ImageCapture.captured_at, ImageCapture.id)
    )
    image_rows, detection_rows = [], []
    for image in images:
        image_detections = _image_detections(image, taxonomies)
        image_rows.append(
            {
                "image_id": str(image.id),
                "camera_name": image.camera.name,
                "timestamp": image.captured_at.timestamp(),
                "image_path": (image.stored_path or "")
                if image.file_status == "moved"
                else image.image_path,
                "detection_count": len(image_detections),
            }
        )
        detection_rows.extend(image_detections)
    return {
        "images": image_rows,
        "detections": detection_rows,
    }


def load_image_detections(
    session: Session, image_capture_id: int
) -> list[dict[str, str | float]]:
    image = session.get(ImageCapture, image_capture_id)
    if image is None:
        raise ValueError("The image no longer exists.")
    taxonomies = {
        taxonomy.id: _species_label(taxonomy)
        for taxonomy in session.scalars(select(Taxonomy))
    }
    return _image_detections(image, taxonomies)
