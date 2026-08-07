# tests/conftest.py

import pytest
from sqlalchemy import create_engine, text, select, func
from sqlalchemy.orm import sessionmaker

from dashboard.db.data_model import Base

from testcontainers.community.postgres import PostgresContainer

from datetime import datetime, UTC

from dashboard.db import (
    camera_crud,
    image_crud,
    ml_model_crud,
    detection_crud,
    detection_correction_crud,
    taxonomy_crud,
    classification_crud,
    classification_correction_crud,
    app_user_crud,
    daily_analysis_result_crud,
)

# for local docker desktop,
# environ["DOCKER_HOST"] is "unix:///home/[user]/.docker/desktop/docker.sock"


@pytest.fixture
def point_str():
    return "SRID=4326;POINT({} {})"


@pytest.fixture
def location_text():
    def _location_text(session, table, row_id):
        statement = select(func.ST_AsEWKT(table.location)).where(table.id == row_id)
        return session.execute(statement).scalar_one()

    return _location_text


def _psycopg_url(connection_url):
    return connection_url.replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    ).replace("postgresql://", "postgresql+psycopg://")


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
    get_session.execute(
        text("""
            TRUNCATE TABLE
                camera_location_history,
                camera,
                image_capture,
                ml_model,
                object_detection,
                taxonomy,
                species_classification,
                app_user,
                detection_correction,
                classification_correction,
                daily_analysis_result
            RESTART IDENTITY CASCADE;
            ALTER SEQUENCE new_detection_id_seq RESTART WITH 1;
            ALTER SEQUENCE new_classification_id_seq RESTART WITH 1;
            """)
    )  # restart identity restart owned sequences, the ALTER commands for manually created sequences
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
        "create_another": {
            "name": "Camera 2",
            "location": (7.5678, 50.1234),
            "description": "Backyard camera",
            "status": "inactive",
            "installation_date": datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        },
        "update": {
            "name": "Camera 1 Updated",
            "location": (7.2234, 50.6678),
            "description": "Updated entrance camera",
            "status": "maintenance",
        },
    }


@pytest.fixture(scope="function")
def created_camera(get_session, camera_data):
    def _create_camera():

        return camera_crud.add(get_session, **camera_data["create"])

    return _create_camera


@pytest.fixture(scope="function")
def created_multi_cameras(get_session, camera_data, created_camera):
    def _create_cameras():
        created_camera()
        camera_crud.add(get_session, **camera_data["create_another"])
        return camera_crud.select(get_session)

    return _create_cameras


@pytest.fixture(scope="function")
def image_data():
    return {
        "create": {
            "camera_id": 1,
            "image_path": "/path/to/image.jpg",
            "location": (7.1234, 50.5678),
            "tobe_deleted": False,
        },
        "create_another": {
            "camera_id": 1,
            "image_path": "/path/to/image_with_timestamps.jpg",
            "location": (7.1234, 50.5678),
            "captured_at": datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            "uploaded_at": datetime(2024, 1, 1, 12, 5, 0, tzinfo=UTC),
            "tobe_deleted": False,
        },
        "update": {
            "tobe_deleted": True,
        },
    }


@pytest.fixture(scope="function")
def created_image(get_session, created_camera, image_data):
    def _create_image():
        created_camera()  # Ensure a camera exists before creating an image
        return image_crud.add(get_session, **image_data["create"])

    return _create_image


@pytest.fixture(scope="function")
def created_multi_images(get_session, image_data, created_image):
    def _create_images():
        created_image()
        image_crud.add(get_session, **image_data["create_another"])
        return image_crud.select(get_session)

    return _create_images


@pytest.fixture(scope="function")
def ml_model_data():
    return {
        "create": {
            "name": "Model 1",
            "version": "v1.0",
            "task": "detection",
            "description": "First detection model",
        },
        "create_another": {
            "name": "Model 2",
            "task": "classification",
        },
        "update": {
            "name": "Model 1 Updated",
            "version": "v1.1",
            "task": "classification",
            "description": "Updated classification model",
        },
    }


@pytest.fixture(scope="function")
def created_ml_model(get_session, ml_model_data):
    def _create_ml_model():
        return ml_model_crud.add(get_session, **ml_model_data["create"])

    return _create_ml_model


@pytest.fixture(scope="function")
def created_multi_ml_models(get_session, ml_model_data, created_ml_model):
    def _create_ml_models():
        created_ml_model()
        ml_model_crud.add(get_session, **ml_model_data["create_another"])
        return ml_model_crud.select(get_session)

    return _create_ml_models


@pytest.fixture(scope="function")
def object_detection_data():
    return {
        "create": {
            "image_capture_id": 1,
            "det_model_id": 1,
            "confidence": 0.95,
            "bbox": {"x": 100, "y": 100, "width": 50, "height": 50},
            "detected_class": "animal",
        },
        "create_another": {
            "image_capture_id": 1,
            "det_model_id": 1,
            "confidence": 0.88,
            "bbox": {"x": 150, "y": 150, "width": 60, "height": 60},
            "detected_class": "vehicle",
        },
        "update": {
            "confidence": 0.98,
            "detected_class": "rodent",
        },
    }


@pytest.fixture(scope="function")
def created_object_detection(
    get_session, object_detection_data, created_image, created_ml_model
):
    def _create_object_detection():
        created_image()  # Ensure an image exists before creating an object detection
        created_ml_model()  # Ensure a model exists before creating an object detection
        return detection_crud.add(get_session, **object_detection_data["create"])

    return _create_object_detection


@pytest.fixture(scope="function")
def created_multi_object_detections(
    get_session, object_detection_data, created_object_detection
):
    def _create_object_detections():
        created_object_detection()
        detection_crud.add(get_session, **object_detection_data["create_another"])
        return detection_crud.select(get_session)

    return _create_object_detections


@pytest.fixture(scope="function")
def taxonomy_data():
    return {
        "create": {
            "species": "Rattus norvegicus",
            "genus": "Rattus",
            "family": "Muridae",
        },
        "create_another": {
            "species": "Mus musculus",
            "genus": "Mus",
            "family": "Muridae",
            "kingdom": "Animalia",
            "phylum": "Chordata",
            "class_name": "Mammalia",
            "order": "Rodentia",
            "common_name": "House mouse",
        },
        "update": {
            "common_name": "Updated common name",
        },
    }


@pytest.fixture(scope="function")
def created_taxonomy(get_session, taxonomy_data):
    def _create_taxonomy():
        return taxonomy_crud.add(get_session, **taxonomy_data["create"])

    return _create_taxonomy


@pytest.fixture(scope="function")
def created_multi_taxonomies(get_session, taxonomy_data, created_taxonomy):
    def _create_taxonomies():
        created_taxonomy()
        taxonomy_crud.add(get_session, **taxonomy_data["create_another"])
        return taxonomy_crud.select(get_session)

    return _create_taxonomies


@pytest.fixture(scope="function")
def species_classification_data():
    return {
        "create": {
            "object_detection_id": 1,
            "taxonomy_id": 1,
            "clas_model_id": 1,
            "confidence": 0.92,
        },
        "create_another": {
            "object_detection_id": 1,
            "taxonomy_id": 1,
            "clas_model_id": 1,
            "confidence": 0.85,
        },
        "update": {
            "confidence": 0.99,
        },
    }


@pytest.fixture(scope="function")
def created_species_classification(
    get_session,
    species_classification_data,
    created_object_detection,
    created_taxonomy,
    created_ml_model,
):
    def _create_species_classification():
        created_object_detection()  # Ensure an object detection exists before creating a species classification
        created_taxonomy()  # Ensure a taxonomy exists before creating a species classification
        created_ml_model()  # Ensure a model exists before creating a species classification
        return classification_crud.add(
            get_session, **species_classification_data["create"]
        )

    return _create_species_classification


@pytest.fixture(scope="function")
def created_multi_species_classifications(
    get_session, species_classification_data, created_species_classification
):
    def _create_species_classifications():
        created_species_classification()
        classification_crud.add(
            get_session, **species_classification_data["create_another"]
        )
        return classification_crud.select(get_session)

    return _create_species_classifications


@pytest.fixture(scope="function")
def app_user_data():
    return {
        "create": {
            "username": "testuser",
            "full_name": "Test User",
            "is_active": True,
        },
        "create_another": {
            "username": "testuser2",
        },
        "update": {
            "full_name": "Updated Test User",
            "is_active": False,
        },
    }


@pytest.fixture(scope="function")
def created_app_user(get_session, app_user_data):
    def _create_app_user():
        return app_user_crud.add(get_session, **app_user_data["create"])

    return _create_app_user


@pytest.fixture(scope="function")
def created_multi_app_users(get_session, app_user_data, created_app_user):
    def _create_app_users():
        created_app_user()
        app_user_crud.add(get_session, **app_user_data["create_another"])
        return app_user_crud.select(get_session)

    return _create_app_users


@pytest.fixture(scope="function")
def detection_correction_data():
    return {
        "create": {
            "object_detection_id": 1,
            "image_capture_id": 1,
            "det_model_id": 1,
            "app_user_id": 1,
            "corrected_bbox": {"x": 110, "y": 110, "width": 45, "height": 45},
            "corrected_class": "rodent",
            "action": "update",
            "comment": "Corrected the detected class and bounding box",
        },
        "create_another": {
            "object_detection_id": None,
            "image_capture_id": 1,
            "det_model_id": 1,
            "app_user_id": 1,
            "corrected_bbox": {"x": 200, "y": 200, "width": 30, "height": 30},
            "corrected_class": "rodent",
            "action": "add",
            "comment": "Adding a new detection",
        },
        "update": {
            "action": "remove",
            "comment": "Removing the detected object",
        },
    }


@pytest.fixture(scope="function")
def created_detection_correction(
    get_session,
    detection_correction_data,
    created_object_detection,
    created_image,
    created_ml_model,
    created_app_user,
):
    def _create_detection_correction():
        created_object_detection()  # Ensure an object detection exists before creating a detection correction
        created_image()  # Ensure an image exists before creating a detection correction
        created_ml_model()  # Ensure a model exists before creating a detection correction
        created_app_user()  # Ensure an app user exists before creating a detection correction
        return detection_correction_crud.add(
            get_session, **detection_correction_data["create"]
        )

    return _create_detection_correction


@pytest.fixture(scope="function")
def created_multi_detection_corrections(
    get_session, detection_correction_data, created_detection_correction
):
    def _create_detection_corrections():
        created_detection_correction()
        detection_correction_crud.add(
            get_session, **detection_correction_data["create_another"]
        )
        return detection_correction_crud.select(get_session)

    return _create_detection_corrections


@pytest.fixture(scope="function")
def classification_correction_data():
    return {
        "create": {
            "species_classification_id": 1,
            "new_obj_det_id": None,
            "app_user_id": 1,
            "corrected_taxonomy_id": 1,
            "action": "update",
            "comment": "Corrected the taxonomy for the classification",
        },
        "create_another": {
            "species_classification_id": None,
            "new_obj_det_id": 1,
            "app_user_id": 1,
            "corrected_taxonomy_id": 1,
            "action": "add",
            "comment": "Adding a new classification correction",
        },
        "update": {
            "action": "update",
            "comment": "Updating the classification correction",
        },
    }


@pytest.fixture(scope="function")
def created_classification_correction(
    get_session,
    created_multi_detection_corrections,
    classification_correction_data,
    created_species_classification,
):
    def _create_classification_correction():
        created_multi_detection_corrections()  # also prepare for create_another case
        created_species_classification()
        return classification_correction_crud.add(
            get_session, **classification_correction_data["create"]
        )

    return _create_classification_correction


@pytest.fixture(scope="function")
def created_multi_classification_corrections(
    get_session,
    classification_correction_data,
    created_classification_correction,
):
    def _create_classification_corrections():
        created_classification_correction()
        classification_correction_crud.add(
            get_session, **classification_correction_data["create_another"]
        )
        return classification_correction_crud.select(get_session)

    return _create_classification_corrections


@pytest.fixture(scope="function")
def daily_analysis_result_data():
    return {
        "create": {
            "camera_id": 1,
            "start_time": datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            "end_time": datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
            "taxonomy_count": 10,
            "avg_confidence": 0.85,
            "taxonomy_id": 1,
        },
        "create_another": {
            "camera_id": 1,
            "start_time": datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
            "end_time": datetime(2024, 1, 3, 0, 0, 0, tzinfo=UTC),
            "taxonomy_count": 15,
            "avg_confidence": 0.80,
            "taxonomy_id": 2,
        },
        "update": {
            "taxonomy_count": 20,
            "avg_confidence": 0.90,
        },
    }


@pytest.fixture(scope="function")
def created_daily_analysis_result(
    get_session,
    daily_analysis_result_data,
    created_camera,
    created_multi_taxonomies,
):
    def _create_daily_analysis_result():
        created_camera()  # Ensure a camera exists before creating a daily analysis result
        created_multi_taxonomies()  # Ensure taxonomies exist before creating a daily analysis result
        return daily_analysis_result_crud.add(
            get_session, **daily_analysis_result_data["create"]
        )

    return _create_daily_analysis_result


@pytest.fixture(scope="function")
def created_multi_daily_analysis_results(
    get_session, daily_analysis_result_data, created_daily_analysis_result
):
    def _create_daily_analysis_results():
        created_daily_analysis_result()
        daily_analysis_result_crud.add(
            get_session, **daily_analysis_result_data["create_another"]
        )
        return daily_analysis_result_crud.select(get_session)

    return _create_daily_analysis_results
