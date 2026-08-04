import pytest
from unittest.mock import Mock, call
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
