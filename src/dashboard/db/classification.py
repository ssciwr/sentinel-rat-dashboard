"""CRUD helpers for the species_classification table"""

from typing import Any

from sqlalchemy import select, DateTime
from sqlalchemy.orm import Session

from .data_model import SpeciesClassification, ClassificationCorrection
from dashboard.db.crud import CRUDBase
from . import utils


class SpeciesClassificationCRUD(CRUDBase[SpeciesClassification]):
    """CRUD helper for the species_classification table."""

    def __init__(self):
        super().__init__(SpeciesClassification)

    def add_species_classification(
        self,
        session: Session,
        *,
        object_detection_id: int,
        taxonomy_id: int,
        clas_model_id: int,
        confidence: float,
        created_at: DateTime | None = None,
    ) -> SpeciesClassification:
        """Insert a new species_classification row and return the persisted object."""

        species_classification = SpeciesClassification(
            object_detection_id=object_detection_id,
            taxonomy_id=taxonomy_id,
            clas_model_id=clas_model_id,
            confidence=confidence,
        )

        if created_at is not None:
            species_classification.created_at = created_at

        session.add(species_classification)
        utils.commit(session)
        session.refresh(species_classification)

        return species_classification

    def update(self, *args, **kwargs) -> None:
        """This method is not intended to be used directly.
        Correction of a classification should be stored in ClassificationCorrection table.
        """
        raise NotImplementedError(
            "Direct update of species_classification is not allowed. "
            "Use ClassificationCorrectionCRUD to store corrections for species classifications."
        )


class ClassificationCorrectionCRUD(CRUDBase[ClassificationCorrection]):
    """CRUD helper for the classification_correction table."""

    def __init__(self):
        super().__init__(ClassificationCorrection)


# Create instances of the CRUD classes for use in other parts of the application
classification_crud = SpeciesClassificationCRUD()
classification_correction_crud = ClassificationCorrectionCRUD()
