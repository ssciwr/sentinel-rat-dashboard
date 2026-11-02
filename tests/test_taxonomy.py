from dashboard.db import taxonomy_crud


def test_is_predator_defaults_to_not_assessed(created_taxonomy):
    assert created_taxonomy().is_predator is None


def test_is_predator_can_be_set(get_session, created_taxonomy):
    taxonomy = created_taxonomy()

    updated = taxonomy_crud.update(get_session, taxonomy.id, is_predator=True)

    assert updated.is_predator is True


def test_filter_by_is_predator(get_session, created_multi_taxonomies):
    not_assessed, prey = created_multi_taxonomies()

    assert taxonomy_crud.filter(get_session, is_predator=False) == [prey]
    assert taxonomy_crud.filter(get_session, is_predator=None) == [not_assessed]
    assert taxonomy_crud.filter(get_session, is_predator=True) == []
