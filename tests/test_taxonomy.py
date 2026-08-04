from dashboard.db import taxonomy
from dashboard.db.data_model import Taxonomy
import pytest


def test_add_taxonomy_creates_row(get_session, taxonomy_data):
    created_taxonomy = taxonomy.add_taxonomy(get_session, **taxonomy_data["create"])

    assert created_taxonomy.id is not None
    assert created_taxonomy.species == taxonomy_data["create"]["species"]
    assert created_taxonomy.genus == taxonomy_data["create"]["genus"]
    assert created_taxonomy.family == taxonomy_data["create"]["family"]
    assert created_taxonomy.kingdom is None

    created_taxonomy_with_optional = taxonomy.add_taxonomy(
        get_session, **taxonomy_data["create_with_optional_fields"]
    )

    assert created_taxonomy_with_optional.id is not None
    assert (
        created_taxonomy_with_optional.species
        == taxonomy_data["create_with_optional_fields"]["species"]
    )
    assert (
        created_taxonomy_with_optional.kingdom
        == taxonomy_data["create_with_optional_fields"]["kingdom"]
    )
    assert (
        created_taxonomy_with_optional.common_name
        == taxonomy_data["create_with_optional_fields"]["common_name"]
    )


def test_select_and_get_taxonomy_return_saved_rows(get_session, taxonomy_data):
    created_taxonomy = taxonomy.add_taxonomy(get_session, **taxonomy_data["create"])

    taxonomies = taxonomy.select_taxonomies(get_session)

    assert len(taxonomies) == 1
    assert taxonomies[0].id == created_taxonomy.id
    assert taxonomies[0].species == taxonomy_data["create"]["species"]

    fetched_taxonomy = taxonomy.get_taxonomy(get_session, created_taxonomy.id)
    assert fetched_taxonomy is not None
    assert fetched_taxonomy.id == created_taxonomy.id
    assert fetched_taxonomy.genus == taxonomy_data["create"]["genus"]


def test_get_taxonomies_by_filter_returns_filtered_rows(get_session, taxonomy_data):
    taxonomy.add_taxonomy(get_session, **taxonomy_data["create"])
    taxonomy.add_taxonomy(get_session, **taxonomy_data["create_with_optional_fields"])

    filtered_taxonomies = taxonomy.get_taxonomies_by_filter(
        get_session, species=taxonomy_data["create"]["species"]
    )

    assert len(filtered_taxonomies) == 1
    assert filtered_taxonomies[0].id == 1
    assert filtered_taxonomies[0].species == taxonomy_data["create"]["species"]

    filtered_taxonomies_by_family = taxonomy.get_taxonomies_by_filter(
        get_session, family=taxonomy_data["create"]["family"]
    )
    assert len(filtered_taxonomies_by_family) == 2


def test_get_taxonomies_by_filter_raises_value_error_when_no_filters(get_session):
    with pytest.raises(ValueError):
        taxonomy.get_taxonomies_by_filter(get_session)


def test_update_taxonomy_updates_fields(get_session, taxonomy_data):
    created_taxonomy = taxonomy.add_taxonomy(get_session, **taxonomy_data["create"])

    updated_taxonomy = taxonomy.update_taxonomy(
        get_session, created_taxonomy.id, **taxonomy_data["update"]
    )

    assert updated_taxonomy is not None
    assert updated_taxonomy.id == created_taxonomy.id
    assert updated_taxonomy.common_name == taxonomy_data["update"]["common_name"]


def test_update_taxonomy_with_no_changes_returns_same_object(
    get_session, taxonomy_data
):
    created_taxonomy = taxonomy.add_taxonomy(get_session, **taxonomy_data["create"])

    updated_taxonomy = taxonomy.update_taxonomy(get_session, created_taxonomy.id)

    assert updated_taxonomy is not None
    assert updated_taxonomy.id == created_taxonomy.id
    assert updated_taxonomy.species == created_taxonomy.species


def test_update_taxonomy_with_unexpected_fields_raises_error(
    get_session, taxonomy_data
):
    created_taxonomy = taxonomy.add_taxonomy(get_session, **taxonomy_data["create"])

    with pytest.raises(ValueError):
        taxonomy.update_taxonomy(
            get_session, created_taxonomy.id, unexpected_field="value"
        )


def test_update_taxonomy_with_nonexistent_id_returns_none(get_session, taxonomy_data):
    created_taxonomy = taxonomy.add_taxonomy(get_session, **taxonomy_data["create"])

    updated_taxonomy = taxonomy.update_taxonomy(get_session, created_taxonomy.id + 1)
    assert updated_taxonomy is None


def test_delete_taxonomy_removes_row(get_session, taxonomy_data):
    created_taxonomy = taxonomy.add_taxonomy(get_session, **taxonomy_data["create"])

    assert taxonomy.delete_taxonomy(get_session, created_taxonomy.id) is True

    deleted_taxonomy = taxonomy.get_taxonomy(get_session, created_taxonomy.id)
    assert deleted_taxonomy is None
