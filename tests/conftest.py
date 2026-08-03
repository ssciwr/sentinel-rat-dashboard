# tests/conftest.py

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from dashboard.db.data_model import Base
from dashboard.db.data_model import (
    Camera,
    CameraLocationHistory,
    ImageCapture,
    Model,
    ObjectDetection,
    Taxonomy,
    SpeciesClassification,
    AppUser,
    DetectionCorrection,
    ClassificationCorrection,
    DailyAnalysisResult,
)

from testcontainers.community.postgres import PostgresContainer

# for local docker desktop,
# environ["DOCKER_HOST"] is "unix:///home/[user]/.docker/desktop/docker.sock"


def _psycopg_url(connection_url):
    return (
        connection_url.replace("postgresql+psycopg2://", "postgresql+psycopg://")
        .replace("postgresql://", "postgresql+psycopg://")
    )


@pytest.fixture(scope="module")
def get_docker_image():
    return "postgis/postgis:17-3.5"


@pytest.fixture(scope="module")
def get_engine_with_tables(get_docker_image):
    with PostgresContainer(get_docker_image) as postgres:
        engine = create_engine(_psycopg_url(postgres.get_connection_url()))
        Base.metadata.create_all(engine)

        yield engine

        Base.metadata.drop_all(engine)


@pytest.fixture(scope="module")
def get_engine_without_tables(get_docker_image):
    with PostgresContainer(get_docker_image) as postgres:
        engine = create_engine(_psycopg_url(postgres.get_connection_url()))

        yield engine

        Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def get_session(get_engine_with_tables):
    connection = get_engine_with_tables.connect()
    session_class = sessionmaker(bind=connection)
    session = session_class()

    yield session

    # tear down
    session.close()
    connection.close()


@pytest.fixture(scope="function", autouse=True)
def clean_db(get_session):
    yield
    get_session.execute(text("""
            TRUNCATE TABLE
                camera_location_history,
                camera,
                image_capture,
                model,
                object_detection,
                taxonomy,
                species_classification,
                app_user,
                detection_correction,
                classification_correction,
                daily_analysis_result
            RESTART IDENTITY CASCADE
            """))
    get_session.commit()


@pytest.fixture(scope="function")
def camera_data():
    return {
        "create": {
            "name": "Camera 1",
            "location": (7.1234, 50.5678),
            "description": "Main entrance camera",
            "status": "active",
        },
        "update": {
            "name": "Camera 1 Updated",
            "location": (7.2234, 50.6678),
            "description": "Updated entrance camera",
            "status": "maintenance",
        },
    }
