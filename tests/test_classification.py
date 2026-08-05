from dashboard.db import classification_crud
import pytest


def test_add_species_classification_creates_row(
    created_species_classification,
    species_classification_data,
):
    created_classification = created_species_classification()

    assert created_classification.id is not None
    assert (
        created_classification.object_detection_id
        == species_classification_data["create"]["object_detection_id"]
    )
    assert (
        created_classification.taxonomy_id
        == species_classification_data["create"]["taxonomy_id"]
    )
    assert (
        created_classification.clas_model_id
        == species_classification_data["create"]["clas_model_id"]
    )
    assert (
        created_classification.confidence
        == species_classification_data["create"]["confidence"]
    )


def test_refuse_update(created_species_classification, species_classification_data):
    created_classification = created_species_classification()

    with pytest.raises(NotImplementedError):
        classification_crud.update(
            session=None,
            id=created_classification.id,
            **species_classification_data["update"],
        )
