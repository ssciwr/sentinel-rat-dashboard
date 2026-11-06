import pytest
from sqlalchemy.exc import IntegrityError

from dashboard.db import ml_model_crud


@pytest.mark.parametrize("conf_threshold", [0.0, 0.5, 1.0, None])
def test_conf_threshold_accepts_values_in_range(get_session, conf_threshold):
    model = ml_model_crud.add(
        get_session, name="model", task="detection", conf_threshold=conf_threshold
    )

    assert model.conf_threshold == conf_threshold


@pytest.mark.parametrize("conf_threshold", [-0.1, 1.1])
def test_conf_threshold_rejects_values_out_of_range(get_session, conf_threshold):
    with pytest.raises(IntegrityError):
        ml_model_crud.add(
            get_session, name="model", task="detection", conf_threshold=conf_threshold
        )
    get_session.rollback()


@pytest.mark.parametrize("conf_threshold", [-0.1, 1.1])
def test_conf_threshold_update_rejects_values_out_of_range(
    get_session, created_ml_model, conf_threshold
):
    model = created_ml_model()

    with pytest.raises(IntegrityError):
        ml_model_crud.update(
            get_session, model.id, allowed_fields=None, conf_threshold=conf_threshold
        )
    get_session.rollback()
