"""
Unit tests for the ApiClient class.

This module tests the interaction with the GitHub and Port APIs, ensuring
that the client handles different API responses correctly.

pytest fixtures are used to mock external dependencies like the configuration
and the requests session.

Pylint warnings for redefined-outer-name and protected-access are disabled
as they are common false positives when using pytest fixtures and testing
internal methods, respectively.
"""
# pylint: disable=redefined-outer-name, protected-access
import unittest.mock
from unittest.mock import MagicMock

import pytest
import requests

from repo_team_mapper.api_client import ApiClient


@pytest.fixture
def mock_config():
    """Provides a mock config object for tests."""
    mock_cfg = MagicMock()
    mock_cfg.PORT_API_URL = "https://api.getport.io/v1"
    mock_cfg.GITHUB_TOKEN = "dummy_github_token"
    mock_cfg.PORT_USER_TEAM_PROPERTY = "team"
    return mock_cfg


@pytest.fixture
def api_client_fixture(mock_config):
    """
    Provides an ApiClient instance with Github and the Port token method patched.
    """
    with unittest.mock.patch('repo_team_mapper.api_client.Github'), \
         unittest.mock.patch('repo_team_mapper.api_client.ApiClient._get_port_token',
                   return_value="fake-token"):
        client = ApiClient(mock_config)
        client._port_session = MagicMock()
        yield client


def test_get_port_user_team_success(api_client_fixture):
    """Test successful retrieval of a user's team list."""
    email = "user@example.com"

    # Arrange
    mock_search_response = MagicMock()
    mock_search_response.raise_for_status.return_value = None
    mock_search_response.json.return_value = {"entities": [{"identifier": "user123"}]}

    mock_entity_response = MagicMock()
    mock_entity_response.raise_for_status.return_value = None
    mock_entity_response.json.return_value = {"entity": {"team": ["team-alpha"]}}

    api_client_fixture._port_session.post.return_value = mock_search_response
    api_client_fixture._port_session.get.return_value = mock_entity_response

    # Act
    teams = api_client_fixture.get_port_user_team(email)

    # Assert
    assert teams == ["team-alpha"]


def test_get_port_user_team_no_user_found(api_client_fixture):
    """Test returning None when the user's email is not found in Port."""
    email = "nouser@example.com"

    # Arrange
    mock_search_response = MagicMock()
    mock_search_response.raise_for_status.return_value = None
    mock_search_response.json.return_value = {"entities": []}  # No entities found

    api_client_fixture._port_session.post.return_value = mock_search_response

    # Act
    teams = api_client_fixture.get_port_user_team(email)

    # Assert
    assert teams is None
    api_client_fixture._port_session.get.assert_not_called()


def test_get_port_user_team_api_search_fails(api_client_fixture):
    """Test handling of an API error during the user search call."""
    email = "user@example.com"
    api_client_fixture._port_session.post.side_effect = requests.exceptions.RequestException(
        "API is down"
    )

    # Act
    teams = api_client_fixture.get_port_user_team(email)

    # Assert
    assert teams is None


def test_get_port_user_team_api_entity_fails(api_client_fixture):
    """Test handling of an API error during the full entity fetch call."""
    email = "user@example.com"

    # Arrange
    mock_search_response = MagicMock()
    mock_search_response.raise_for_status.return_value = None
    mock_search_response.json.return_value = {"entities": [{"identifier": "user123"}]}

    api_client_fixture._port_session.post.return_value = mock_search_response
    api_client_fixture._port_session.get.side_effect = requests.exceptions.RequestException(
        "API is down"
    )

    # Act
    teams = api_client_fixture.get_port_user_team(email)

    # Assert
    assert teams is None


def test_get_port_user_team_no_teams_property(api_client_fixture):
    """Test returning None if 'team' property is missing from user entity."""
    email = "userwithnoteamprop@example.com"

    # Arrange
    mock_search_response = MagicMock()
    mock_search_response.raise_for_status.return_value = None
    mock_search_response.json.return_value = {"entities": [{"identifier": "user123"}]}

    mock_entity_response = MagicMock()
    mock_entity_response.raise_for_status.return_value = None
    mock_entity_response.json.return_value = {"entity": {"some_other_key": "value"}}

    api_client_fixture._port_session.post.return_value = mock_search_response
    api_client_fixture._port_session.get.return_value = mock_entity_response

    # Act
    teams = api_client_fixture.get_port_user_team(email)

    # Assert
    assert teams is None


def test_get_port_user_team_empty_teams_list(api_client_fixture):
    """Test returning empty list if user's team list is empty."""
    email = "userwithemptyteams@example.com"

    # Arrange
    mock_search_response = MagicMock()
    mock_search_response.raise_for_status.return_value = None
    mock_search_response.json.return_value = {"entities": [{"identifier": "user123"}]}

    mock_entity_response = MagicMock()
    mock_entity_response.raise_for_status.return_value = None
    mock_entity_response.json.return_value = {"entity": {"team": []}}

    api_client_fixture._port_session.post.return_value = mock_search_response
    api_client_fixture._port_session.get.return_value = mock_entity_response

    # Act
    teams = api_client_fixture.get_port_user_team(email)

    # Assert
    assert teams == []
