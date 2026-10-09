"""CRUD helpers for the species_classification table"""

import warnings
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Sequence, func, select
from sqlalchemy.orm import Session

from dashboard.db.crud import CRUDBase

from . import utils
from .analysis_result import daily_analysis_result_crud
from .data_model import (
    ClassificationCorrection,
    DetectionCorrection,
    SpeciesClassification,
)


class SpeciesClassificationCRUD(CRUDBase[SpeciesClassification]):
    """CRUD helper for the species_classification table."""

    def __init__(self):
        super().__init__(SpeciesClassification)

    def add(
        self,
        session: Session,
        *,
        object_detection_id: int,
        taxonomy_id: int,
        clas_model_id: int,
        confidence: float,
        created_at: datetime | None = None,
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

    def add(
        self,
        session: Session,
        *,
        species_classification_id: int | None,
        new_obj_det_id: int | None,
        app_user_id: int,
        corrected_taxonomy_id: int,
        comment: str | None = None,
        last_updated: datetime | None = None,
        action: Literal["add", "update"] = "update",
    ) -> ClassificationCorrection:
        """Insert a new classification_correction row and return the persisted object."""

        classification_correction = ClassificationCorrection(
            species_classification_id=species_classification_id,
            new_obj_det_id=new_obj_det_id,
            app_user_id=app_user_id,
            corrected_taxonomy_id=corrected_taxonomy_id,
            comment=comment,
            action=action,
        )

        # in case of a new detection correction is added into DetectionCorrection table
        # a new_classification_id will be generated as the next sequence value across rows
        # this only happens when action is "add", species_classification_id is None,
        # and new_obj_det_id is fetched from the newly added detection correction,
        # which is done in the application layer.
        if species_classification_id is None and action == "add":
            if new_obj_det_id is None:
                raise ValueError(
                    "new_obj_det_id must be provided when adding a new classification correction "
                    "for a newly added detection correction, "
                )

            classification_seq = Sequence("new_classification_id_seq")
            next_new_classification_id = session.scalar(
                select(classification_seq.next_value())
            )
            classification_correction.new_classification_id = next_new_classification_id
        elif species_classification_id is not None and action != "add":
            # no new classification is added
            if new_obj_det_id is not None:
                warnings.warn(
                    "new_obj_det_id is provided but species_classification_id is not None "
                    "and action is not 'add', "
                    "which is used when the new classification correction does not "
                    "correspond to a newly added detection correction. "
                    "Therefore, new_obj_det_id will be ignored."
                )
            classification_correction.new_classification_id = None
        elif species_classification_id is None and action != "add":
            raise ValueError(
                "species_classification_id must be provided unless action is 'add'."
            )
        else:
            raise ValueError(
                "species_classification_id must be None when action is 'add'."
            )

        if last_updated is not None:
            classification_correction.last_updated = last_updated

        session.add(classification_correction)
        # a correction of an already aggregated image changes its daily results
        daily_analysis_result_crud.commit_with_recompute(
            session, self._image_capture_id(session, classification_correction)
        )
        session.refresh(classification_correction)

        return classification_correction

    def update(
        self,
        session: Session,
        classification_correction_id: int,
        **changes: Any,
    ) -> ClassificationCorrection | None:
        """Update a classification_correction row and return the refreshed object, or None if missing."""

        classification_correction = session.get(
            self.model, classification_correction_id
        )
        if classification_correction is None:
            return None

        non_pk_fk_fields = {
            col.name
            for col in ClassificationCorrection.__table__.columns
            if not col.primary_key and not col.foreign_keys
        }

        # the corrected species can change, the corrected item and the user can't
        allowed_fields = non_pk_fk_fields - {
            "new_obj_det_id",
            "last_updated",
        } | {"corrected_taxonomy_id"}

        unsupported_fields = set(changes.keys()) - allowed_fields
        if unsupported_fields:
            raise ValueError(
                f"Unsupported classification_correction fields: {sorted(unsupported_fields)}"
            )

        # raise error if action is updated to "add"
        if "action" in changes and changes["action"] == "add":
            raise ValueError(
                "Direct update of action to 'add' is not allowed. "
                "Use the add() method to create a new classification correction."
            )

        if not changes:
            return classification_correction

        # update last_updated to current timestamp
        classification_correction.last_updated = func.now()

        super().update(
            session,
            classification_correction_id,
            allowed_fields=allowed_fields,
            commit=False,
            **changes,
        )
        daily_analysis_result_crud.commit_with_recompute(
            session, self._image_capture_id(session, classification_correction)
        )
        session.refresh(classification_correction)
        return classification_correction

    def delete(self, session: Session, id: int) -> bool:
        """Delete a classification_correction row and rebuild the daily results of
        its image if they used it. Return True if deleted."""

        classification_correction = session.get(ClassificationCorrection, id)
        if classification_correction is None:
            return False

        image_capture_id = self._image_capture_id(session, classification_correction)
        session.delete(classification_correction)
        daily_analysis_result_crud.commit_with_recompute(session, image_capture_id)
        return True

    def _image_capture_id(
        self, session: Session, classification_correction: ClassificationCorrection
    ) -> int | None:
        """Return the id of the image a classification correction belongs to,
        or None if its classification or added detection doesn't exist."""

        if classification_correction.species_classification_id is not None:
            classification = session.get(
                SpeciesClassification,
                classification_correction.species_classification_id,
            )
            if classification is None:
                return None
            return classification.object_detection.image_capture_id

        detection_correction = session.scalars(
            select(DetectionCorrection).where(
                DetectionCorrection.new_detection_id
                == classification_correction.new_obj_det_id
            )
        ).first()
        if detection_correction is None:
            return None
        return detection_correction.image_capture_id


# Create instances of the CRUD classes for use in other parts of the application
classification_crud = SpeciesClassificationCRUD()
classification_correction_crud = ClassificationCorrectionCRUD()
