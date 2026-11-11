import pytest
from sqlalchemy.exc import IntegrityError

from dashboard.db import (
    daily_analysis_result_crud,
)
from dashboard.db.analysis_result import (
    _resolve_thresholds,
    day_bounds,
)

from .helpers import (
    DAY,
    TZ,
    add_detection,
    add_image,
    at,
    compute,
)


def _row_values(setup, **kwargs):
    start, end = day_bounds(DAY, TZ)
    return {
        "camera_id": setup.camera1.id,
        "start_time": start,
        "end_time": end,
        "det_model_id": setup.det_model.id,
        "taxonomy_id": setup.rat.id,
        "taxonomy_count": 1,
        "avg_confidence": 0.9,
        "det_threshold": 0.5,
        "clas_threshold": 0.5,
        "image_count": 1,
    } | kwargs


@pytest.mark.parametrize("column", ["det_threshold", "clas_threshold", "image_count"])
def test_thresholds_and_image_count_are_required(get_session, setup, column):
    values = _row_values(setup)
    del values[column]

    with pytest.raises(IntegrityError):
        daily_analysis_result_crud.add(get_session, **values)
    get_session.rollback()


@pytest.mark.parametrize("column", ["det_threshold", "clas_threshold"])
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_thresholds_must_be_between_zero_and_one(get_session, setup, column, value):
    values = _row_values(setup, **{column: value})

    with pytest.raises(IntegrityError):
        daily_analysis_result_crud.add(get_session, **values)
    get_session.rollback()


@pytest.mark.parametrize("column", ["det_threshold", "clas_threshold"])
@pytest.mark.parametrize("value", [0.0, 1.0])
def test_thresholds_accept_their_limits(get_session, setup, column, value):
    row = daily_analysis_result_crud.add(
        get_session, **_row_values(setup, **{column: value})
    )

    assert getattr(row, column) == value


@pytest.mark.parametrize("column", ["det_threshold", "clas_threshold"])
def test_thresholds_are_not_part_of_the_unique_key(get_session, setup, column):
    daily_analysis_result_crud.add(get_session, **_row_values(setup))
    duplicate = _row_values(setup, **{column: 0.9})

    with pytest.raises(IntegrityError):
        daily_analysis_result_crud.add(get_session, **duplicate)
    get_session.rollback()


def test_compute_stores_zero_thresholds(get_session, setup):
    image = add_image(get_session, setup, at(10))
    add_detection(get_session, setup, image, [(setup.rat, 0.9)])

    rows = compute(get_session)

    assert [(row.det_threshold, row.clas_threshold) for row in rows] == [(0.0, 0.0)]


def test_thresholds_default_to_zero():
    assert _resolve_thresholds(None, None) == (0.0, 0.0)


def test_thresholds_default_to_environment(monkeypatch):
    monkeypatch.setenv("DET_CONF_THRESHOLD", "0.4")
    monkeypatch.setenv("CLAS_CONF_THRESHOLD", " 0.6 ")

    assert _resolve_thresholds(None, None) == (0.4, 0.6)


@pytest.mark.parametrize("env_name", ["DET_CONF_THRESHOLD", "CLAS_CONF_THRESHOLD"])
def test_each_threshold_uses_its_own_environment_variable(monkeypatch, env_name):
    monkeypatch.setenv(env_name, "0.4")

    expected = (0.4, 0.0) if env_name == "DET_CONF_THRESHOLD" else (0.0, 0.4)
    assert _resolve_thresholds(None, None) == expected


def test_empty_environment_threshold_is_not_set(monkeypatch):
    monkeypatch.setenv("DET_CONF_THRESHOLD", "")
    monkeypatch.setenv("CLAS_CONF_THRESHOLD", "  ")

    assert _resolve_thresholds(None, None) == (0.0, 0.0)


def test_given_thresholds_replace_environment(monkeypatch):
    monkeypatch.setenv("DET_CONF_THRESHOLD", "0.4")
    monkeypatch.setenv("CLAS_CONF_THRESHOLD", "0.6")

    assert _resolve_thresholds(0.7, 0.0) == (0.7, 0.0)


def test_given_threshold_ignores_invalid_environment(monkeypatch):
    monkeypatch.setenv("DET_CONF_THRESHOLD", "high")

    assert _resolve_thresholds(0.7, None) == (0.7, 0.0)


@pytest.mark.parametrize("env_name", ["DET_CONF_THRESHOLD", "CLAS_CONF_THRESHOLD"])
@pytest.mark.parametrize("value", ["high", "1.5", "-0.1", "nan"])
def test_invalid_environment_threshold_is_refused(
    get_session, setup, monkeypatch, env_name, value
):
    monkeypatch.setenv(env_name, value)
    image = add_image(get_session, setup, at(10))

    with pytest.raises(ValueError, match=env_name):
        compute(get_session)

    get_session.refresh(image)
    assert image.analyzed_at is None


@pytest.mark.parametrize("parameter", ["det_threshold", "clas_threshold"])
@pytest.mark.parametrize("value", [-0.1, 1.5, float("nan")])
def test_invalid_given_threshold_is_refused(get_session, setup, parameter, value):
    image = add_image(get_session, setup, at(10))

    with pytest.raises(ValueError, match=parameter):
        compute(get_session, **{parameter: value})

    get_session.refresh(image)
    assert image.analyzed_at is None
