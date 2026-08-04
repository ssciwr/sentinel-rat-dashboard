from dashboard.db import analysis_result, camera, taxonomy
from dashboard.db.data_model import DailyAnalysisResult
import pytest


def _add_daily_analysis_result(
    session, camera_data, taxonomy_data, daily_analysis_result_data
):
    camera.add_camera(session, **camera_data["create"])
    taxonomy.add_taxonomy(session, **taxonomy_data["create"])
    taxonomy.add_taxonomy(session, **taxonomy_data["create_with_optional_fields"])
    return analysis_result.add_daily_analysis_result(
        session, **daily_analysis_result_data["create"]
    )


def test_add_daily_analysis_result_creates_row(
    get_session,
    camera_data,
    taxonomy_data,
    daily_analysis_result_data,
):
    created_result = _add_daily_analysis_result(
        get_session, camera_data, taxonomy_data, daily_analysis_result_data
    )

    assert created_result.id is not None
    assert created_result.camera_id == daily_analysis_result_data["create"]["camera_id"]
    assert (
        created_result.start_time == daily_analysis_result_data["create"]["start_time"]
    )
    assert created_result.end_time == daily_analysis_result_data["create"]["end_time"]
    assert (
        created_result.taxonomy_count
        == daily_analysis_result_data["create"]["taxonomy_count"]
    )
    assert (
        created_result.avg_confidence
        == daily_analysis_result_data["create"]["avg_confidence"]
    )
    assert (
        created_result.taxonomy_id
        == daily_analysis_result_data["create"]["taxonomy_id"]
    )


def test_select_and_get_daily_analysis_result_return_saved_rows(
    get_session, camera_data, taxonomy_data, daily_analysis_result_data
):
    created_result = _add_daily_analysis_result(
        get_session, camera_data, taxonomy_data, daily_analysis_result_data
    )

    results = analysis_result.select_daily_analysis_results(get_session)

    assert len(results) == 1
    assert results[0].id == created_result.id
    assert results[0].camera_id == daily_analysis_result_data["create"]["camera_id"]

    fetched_result = analysis_result.get_daily_analysis_result(
        get_session, created_result.id
    )
    assert fetched_result is not None
    assert fetched_result.id == created_result.id
    assert (
        fetched_result.taxonomy_count
        == daily_analysis_result_data["create"]["taxonomy_count"]
    )


def test_get_daily_analysis_results_by_filter_returns_filtered_rows(
    get_session, camera_data, taxonomy_data, daily_analysis_result_data
):
    created_result1 = _add_daily_analysis_result(
        get_session, camera_data, taxonomy_data, daily_analysis_result_data
    )

    created_result2 = analysis_result.add_daily_analysis_result(
        get_session, **daily_analysis_result_data["create_another"]
    )

    filtered_results = analysis_result.get_daily_analysis_results_by_filter(
        get_session, camera_id=daily_analysis_result_data["create"]["camera_id"]
    )

    assert len(filtered_results) == 2
    assert filtered_results[0].id == created_result1.id
    assert filtered_results[1].id == created_result2.id


def test_get_daily_analysis_results_by_filter_raises_value_error_when_no_filters(
    get_session,
):
    with pytest.raises(ValueError):
        analysis_result.get_daily_analysis_results_by_filter(get_session)


def test_update_daily_analysis_result_updates_fields(
    get_session, camera_data, taxonomy_data, daily_analysis_result_data
):
    created_result = _add_daily_analysis_result(
        get_session, camera_data, taxonomy_data, daily_analysis_result_data
    )

    updated_result = analysis_result.update_daily_analysis_result(
        get_session, created_result.id, **daily_analysis_result_data["update"]
    )

    assert updated_result is not None
    assert updated_result.id == created_result.id
    assert (
        updated_result.taxonomy_count
        == daily_analysis_result_data["update"]["taxonomy_count"]
    )
    assert (
        updated_result.avg_confidence
        == daily_analysis_result_data["update"]["avg_confidence"]
    )


def test_update_daily_analysis_result_with_no_changes_returns_same_object(
    get_session, camera_data, taxonomy_data, daily_analysis_result_data
):
    created_result = _add_daily_analysis_result(
        get_session, camera_data, taxonomy_data, daily_analysis_result_data
    )

    updated_result = analysis_result.update_daily_analysis_result(
        get_session, created_result.id
    )

    assert updated_result is not None
    assert updated_result.id == created_result.id
    assert updated_result.taxonomy_count == created_result.taxonomy_count


def test_update_daily_analysis_result_with_unexpected_fields_raises_error(
    get_session, camera_data, taxonomy_data, daily_analysis_result_data
):
    created_result = _add_daily_analysis_result(
        get_session, camera_data, taxonomy_data, daily_analysis_result_data
    )

    with pytest.raises(ValueError):
        analysis_result.update_daily_analysis_result(
            get_session, created_result.id, unexpected_field="value"
        )


def test_update_daily_analysis_result_with_nonexistent_id_returns_none(
    get_session, camera_data, taxonomy_data, daily_analysis_result_data
):
    created_result = _add_daily_analysis_result(
        get_session, camera_data, taxonomy_data, daily_analysis_result_data
    )

    updated_result = analysis_result.update_daily_analysis_result(
        get_session, created_result.id + 1
    )
    assert updated_result is None


def test_delete_daily_analysis_result_removes_row(
    get_session, camera_data, taxonomy_data, daily_analysis_result_data
):
    created_result = _add_daily_analysis_result(
        get_session, camera_data, taxonomy_data, daily_analysis_result_data
    )

    assert (
        analysis_result.delete_daily_analysis_result(get_session, created_result.id)
        is True
    )

    deleted_result = analysis_result.get_daily_analysis_result(
        get_session, created_result.id
    )
    assert deleted_result is None
