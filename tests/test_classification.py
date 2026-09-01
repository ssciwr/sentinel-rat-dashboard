import pytest

from dashboard.db import classification_correction_crud, classification_crud


# test for SpeciesClassificationCRUD
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


# test for ClassificationCorrectionCRUD
def test_add_classification_correction_creates_row(
    created_classification_correction,
    classification_correction_data,
):
    created_correction = created_classification_correction()

    assert created_correction.id is not None
    for field, expected_value in classification_correction_data["create"].items():
        actual_value = getattr(created_correction, field)
        assert actual_value == expected_value
    assert created_correction.new_classification_id is None


def test_add_classification_correction_with_add_action(
    created_multi_classification_corrections,
    classification_correction_data,
):
    multi_corrections = created_multi_classification_corrections()
    created_correction = multi_corrections[0]
    created_correction_add = multi_corrections[1]

    assert (
        created_correction.species_classification_id
        == classification_correction_data["create"]["species_classification_id"]
    )
    assert created_correction_add.species_classification_id is None
    assert created_correction_add.action == "add"
    assert created_correction_add.new_classification_id == 1


def test_add_classification_correction_with_errors(
    get_session,
    created_classification_correction,
    classification_correction_data,
):
    # create a valid correction first
    _ = created_classification_correction()

    # None species_classification_id
    # add action
    # None new_obj_det_id
    sample_data = classification_correction_data["create"].copy()
    sample_data["species_classification_id"] = None
    sample_data["action"] = "add"
    sample_data["new_obj_det_id"] = None
    with pytest.raises(ValueError):
        classification_correction_crud.add(get_session, **sample_data)

    # None species_classification_id
    # not add action
    sample_data = classification_correction_data["create"].copy()
    sample_data["species_classification_id"] = None
    with pytest.raises(ValueError):
        classification_correction_crud.add(get_session, **sample_data)

    # not None species_classification_id
    # add action
    sample_data = classification_correction_data["create"].copy()
    sample_data["species_classification_id"] = 1
    sample_data["action"] = "add"
    with pytest.raises(ValueError):
        classification_correction_crud.add(get_session, **sample_data)


def test_add_classification_correction_with_warning(
    get_session,
    classification_correction_data,
    created_multi_detection_corrections,
    created_species_classification,
):
    # not None species_classification_id
    # not add action
    # not None new_obj_det_id
    sample_data = classification_correction_data["create"].copy()
    sample_data["new_obj_det_id"] = 1
    created_multi_detection_corrections()
    created_species_classification()
    with pytest.warns(UserWarning):
        add_item = classification_correction_crud.add(get_session, **sample_data)

    assert add_item.new_classification_id is None


def test_update_classification_correction_update_fields(
    get_session,
    created_classification_correction,
    classification_correction_data,
):
    created_correction = created_classification_correction()

    last_updated_before = created_correction.last_updated

    updated_correction = classification_correction_crud.update(
        get_session, created_correction.id, **classification_correction_data["update"]
    )

    last_updated_after = updated_correction.last_updated

    assert updated_correction is not None
    assert updated_correction.id == created_correction.id
    for field, expected_value in classification_correction_data["update"].items():
        actual_value = getattr(updated_correction, field)
        assert actual_value == expected_value

    assert last_updated_after > last_updated_before
