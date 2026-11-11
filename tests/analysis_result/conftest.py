from types import SimpleNamespace

import pytest

from dashboard.db import (
    app_user_crud,
    camera_crud,
    ml_model_crud,
    taxonomy_crud,
)


@pytest.fixture(autouse=True)
def no_threshold_env(monkeypatch):
    """Keep thresholds of the developer's environment out of the tests."""
    monkeypatch.delenv("DET_CONF_THRESHOLD", raising=False)
    monkeypatch.delenv("CLAS_CONF_THRESHOLD", raising=False)


@pytest.fixture
def setup(get_session):
    session = get_session
    return SimpleNamespace(
        camera1=camera_crud.add(session, name="CAM01", location=(80.6, 7.3)),
        camera2=camera_crud.add(session, name="CAM02", location=(80.7, 7.4)),
        det_model=ml_model_crud.add(session, name="megadetector", task="detection"),
        det_model2=ml_model_crud.add(session, name="yolo", task="detection"),
        clas_model=ml_model_crud.add(session, name="rodent", task="classification"),
        clas_model2=ml_model_crud.add(session, name="other", task="classification"),
        rat=taxonomy_crud.add(session, genus="Rattus", species="rattus"),
        mouse=taxonomy_crud.add(session, genus="Mus", species="musculus"),
        user1=app_user_crud.add(session, username="user1", password="encoded-1"),
        user2=app_user_crud.add(session, username="user2", password="encoded-2"),
    )
