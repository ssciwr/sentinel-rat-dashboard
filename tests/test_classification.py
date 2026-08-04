from dashboard.db import (
    classification,
    camera,
    image,
    ml_model,
    taxonomy,
    detection,
)
import pytest


def _add_species_classification(
    session,
    camera_data,
    image_data,
    ml_model_data,
    object_detection_data,
    taxonomy_data,
    classification_data,
):
    camera.add_camera(session, **camera_data["create"])
    image.add_image_capture(session, **image_data["create"])
    ml_model.add_ml_model(session, **ml_model_data["create"])
    detection.add_object_detection(session, **object_detection_data["create"])
    taxonomy.add_taxonomy(session, **taxonomy_data["create"])
    return classification.add_species_classification(
        session, **classification_data["create"]
    )


def test_add_species_classification_creates_row(
    get_session,
    camera_data,
    image_data,
    ml_model_data,
    object_detection_data,
    taxonomy_data,
    species_classification_data,
):
    created_classification = _add_species_classification(
        get_session,
        camera_data,
        image_data,
        ml_model_data,
        object_detection_data,
        taxonomy_data,
        species_classification_data,
    )

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


def test_select_and_get_species_classification_return_saved_rows(
    get_session,
    camera_data,
    image_data,
    ml_model_data,
    object_detection_data,
    taxonomy_data,
    species_classification_data,
):
    created_classification = _add_species_classification(
        get_session,
        camera_data,
        image_data,
        ml_model_data,
        object_detection_data,
        taxonomy_data,
        species_classification_data,
    )

    classifications = classification.select_species_classifications(get_session)

    assert len(classifications) == 1
    assert classifications[0].id == created_classification.id
    assert (
        classifications[0].taxonomy_id
        == species_classification_data["create"]["taxonomy_id"]
    )

    fetched_classification = classification.get_species_classification(
        get_session, created_classification.id
    )
    assert fetched_classification is not None
    assert fetched_classification.id == created_classification.id
    assert (
        fetched_classification.confidence
        == species_classification_data["create"]["confidence"]
    )


def test_get_species_classifications_by_filter_returns_filtered_rows(
    get_session,
    camera_data,
    image_data,
    ml_model_data,
    object_detection_data,
    taxonomy_data,
    species_classification_data,
):
    created_classification1 = _add_species_classification(
        get_session,
        camera_data,
        image_data,
        ml_model_data,
        object_detection_data,
        taxonomy_data,
        species_classification_data,
    )

    created_classification2 = classification.add_species_classification(
        get_session, **species_classification_data["create_another"]
    )

    filtered_classifications = classification.get_species_classifications_by_filter(
        get_session, taxonomy_id=species_classification_data["create"]["taxonomy_id"]
    )

    assert len(filtered_classifications) == 2
    assert filtered_classifications[0].id == created_classification1.id
    assert filtered_classifications[1].id == created_classification2.id


def test_get_species_classifications_by_filter_raises_value_error_when_no_filters(
    get_session,
):
    with pytest.raises(ValueError):
        classification.get_species_classifications_by_filter(get_session)


def test_update_species_classification_updates_fields(
    get_session,
    camera_data,
    image_data,
    ml_model_data,
    object_detection_data,
    taxonomy_data,
    species_classification_data,
):
    created_classification = _add_species_classification(
        get_session,
        camera_data,
        image_data,
        ml_model_data,
        object_detection_data,
        taxonomy_data,
        species_classification_data,
    )

    updated_classification = classification.update_species_classification(
        get_session, created_classification.id, **species_classification_data["update"]
    )

    assert updated_classification is not None
    assert updated_classification.id == created_classification.id
    assert (
        updated_classification.confidence
        == species_classification_data["update"]["confidence"]
    )


def test_update_species_classification_with_no_changes_returns_same_object(
    get_session,
    camera_data,
    image_data,
    ml_model_data,
    object_detection_data,
    taxonomy_data,
    species_classification_data,
):
    created_classification = _add_species_classification(
        get_session,
        camera_data,
        image_data,
        ml_model_data,
        object_detection_data,
        taxonomy_data,
        species_classification_data,
    )

    updated_classification = classification.update_species_classification(
        get_session, created_classification.id
    )

    assert updated_classification is not None
    assert updated_classification.id == created_classification.id
    assert updated_classification.confidence == created_classification.confidence


def test_update_species_classification_with_unexpected_fields_raises_error(
    get_session,
    camera_data,
    image_data,
    ml_model_data,
    object_detection_data,
    taxonomy_data,
    species_classification_data,
):
    created_classification = _add_species_classification(
        get_session,
        camera_data,
        image_data,
        ml_model_data,
        object_detection_data,
        taxonomy_data,
        species_classification_data,
    )

    with pytest.raises(ValueError):
        classification.update_species_classification(
            get_session, created_classification.id, unexpected_field="value"
        )


def test_update_species_classification_with_nonexistent_id_returns_none(
    get_session,
    camera_data,
    image_data,
    ml_model_data,
    object_detection_data,
    taxonomy_data,
    species_classification_data,
):
    created_classification = _add_species_classification(
        get_session,
        camera_data,
        image_data,
        ml_model_data,
        object_detection_data,
        taxonomy_data,
        species_classification_data,
    )

    updated_classification = classification.update_species_classification(
        get_session, created_classification.id + 1
    )
    assert updated_classification is None


def test_delete_species_classification_removes_row(
    get_session,
    camera_data,
    image_data,
    ml_model_data,
    object_detection_data,
    taxonomy_data,
    species_classification_data,
):
    created_classification = _add_species_classification(
        get_session,
        camera_data,
        image_data,
        ml_model_data,
        object_detection_data,
        taxonomy_data,
        species_classification_data,
    )

    assert (
        classification.delete_species_classification(
            get_session, created_classification.id
        )
        is True
    )

    deleted_classification = classification.get_species_classification(
        get_session, created_classification.id
    )
    assert deleted_classification is None
