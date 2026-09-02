from unittest.mock import Mock

import pytest

from dashboard.db import utils


def test_normalize_location():
    # Test with a tuple
    location = (12.34, 56.78)
    expected = "SRID=4326;POINT(12.34 56.78)"
    assert utils.normalize_location(location) == expected

    # Test with a string
    location_str = "SRID=4326;POINT(12.34 56.78)"
    assert utils.normalize_location(location_str) == location_str

    # Test with an invalid input
    with pytest.raises(ValueError):
        utils.normalize_location("invalid_location")


def test_location_to_text(get_session, camera_data, point_str):
    from dashboard.db.camera import camera_crud
    from dashboard.db.data_model import Camera

    created_camera = camera_crud.add(get_session, **camera_data["create"])

    # Use location_to_text to get the location as text
    location_text = utils.location_to_text(get_session, Camera, created_camera.id)

    expected_location_text = point_str.format(
        camera_data["create"]["location"][0], camera_data["create"]["location"][1]
    )
    assert location_text == expected_location_text


def test_commit_success():
    # get mock session instead of get_session fixture
    session = Mock()
    utils.commit(session)
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_commit_failure():
    # get mock session instead of get_session fixture
    session = Mock()
    session.commit.side_effect = Exception("Commit failed")

    with pytest.raises(Exception, match="Commit failed"):
        utils.commit(session)

    session.commit.assert_called_once()
    session.rollback.assert_called_once()
