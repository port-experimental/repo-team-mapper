"""
This module contains the ApiClient class, which is responsible for all interactions
with the GitHub and Port APIs.
"""
import logging
import time

import requests
from github import Github, GithubException

# Default timeout for all API requests
TIMEOUT = 30


class ApiClient:
    """A unified client for GitHub and Port APIs."""

    def __init__(self, config_obj):
        self.logger = logging.getLogger(__name__)
        self._config = config_obj
        # Enable auto-retry with backoff, which respects GitHub's rate-limiting headers.
        # This will cause the script to "sleep" when it hits a rate limit and resume automatically.
        self._github_client = Github(config_obj.GITHUB_TOKEN, retry=5)
        self._port_access_token = None
        self._port_session = requests.Session()

    def _get_port_token(self):
        """Retrieves and caches the Port API access token."""
        if self._port_access_token:
            return self._port_access_token

        self.logger.info("Requesting new Port API access token.")
        credentials = {
            "clientId": self._config.PORT_CLIENT_ID,
            "clientSecret": self._config.PORT_CLIENT_SECRET,
        }
        try:
            response = requests.post(
                f"{self._config.PORT_API_URL}/auth/access_token",
                json=credentials,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            self._port_access_token = response.json()["accessToken"]
            self._port_session.headers.update(
                {"Authorization": f"Bearer {self._port_access_token}"}
            )
            return self._port_access_token
        except requests.exceptions.RequestException as e:
            self.logger.error("Failed to get Port access token: %s", e)
            raise

    def get_all_organization_repos(self):
        """Fetches all repositories for the configured GitHub organization."""
        self.logger.info("Fetching all repositories from the organization...")

        for attempt in range(3):  # Retry up to 3 times
            try:
                org = self._github_client.get_organization(self._config.GITHUB_ORG)
                return org.get_repos()
            except GithubException as e:
                self.logger.warning(
                    "Attempt %d/3: Failed to fetch repos: %s. Retrying in 5 seconds...",
                    attempt + 1,
                    e,
                )
                time.sleep(5)
            # A broad exception is caught here to prevent a worker thread from crashing.
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.error(
                    "An unexpected error occurred on attempt %d/3: %s", attempt + 1, e
                )
                time.sleep(5)

        self.logger.error("Failed to fetch repositories after multiple retries.")
        return []

    def get_repo(self, repo_full_name):
        """Fetches a single repository object by its full name."""
        try:
            self.logger.info("Fetching repository: %s", repo_full_name)
            repo = self._github_client.get_repo(repo_full_name)
            return repo
        except GithubException as e:
            self.logger.error(
                "Failed to get repository '%s' from GitHub: %s", repo_full_name, e
            )
            return None

    def get_top_committers(self, repo):
        """
        Gets the top committers for a repository based on commit stats.
        Note: This relies on the user's public email in their GitHub profile.
        """
        self.logger.info("Fetching top committers for repo: %s", repo.full_name)
        try:
            # This can be a long-running operation on GitHub's side.
            # PyGithub handles the 202 polling automatically.
            stats = repo.get_stats_contributors()
            if not stats:
                self.logger.warning(
                    "No contributor stats found for repo: %s", repo.full_name
                )
                return []

            # Sort by total commits and take the top N
            sorted_contributors = sorted(stats, key=lambda s: s.total, reverse=True)
            top_contributors = sorted_contributors[: self._config.TOP_COMMITTERS_COUNT]

            committer_details = []
            for contributor in top_contributors:
                user = contributor.author
                if user and user.email:
                    committer_details.append({"email": user.email, "login": user.login})
                else:
                    self.logger.warning(
                        "Committer '%s' in repo '%s' has no public email.",
                        user.login,
                        repo.full_name,
                    )
            return committer_details
        except (GithubException, requests.exceptions.RequestException) as e:
            self.logger.error(
                "Could not get contributor stats for %s: %s", repo.full_name, e
            )
            return []

    def get_port_user_team(self, email):
        """
        Finds a user in Port by email and returns their associated list of team
        IDENTIFIERS. This is a two-step process:
        1. Search for the user by email to get their identifier.
        2. Fetch the user's full entity to get their relations.
        """
        self._get_port_token()
        self.logger.info("Step 1: Searching for Port user with email: %s", email)

        # Step 1: Find the user's identifier
        search_payload = {
            "rules": [
                {"property": "$blueprint", "operator": "=", "value": "_user"},
                {"property": "$identifier", "operator": "=", "value": email},
            ],
            "combinator": "and",
        }
        try:
            response = self._port_session.post(
                f"{self._config.PORT_API_URL}/entities/search",
                json=search_payload,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            entities = response.json().get("entities", [])

            if not entities:
                self.logger.info("No Port user found for email: %s", email)
                return None

            user_identifier = entities[0]["identifier"]
            self.logger.info(
                "Step 2: Found user. Fetching details for identifier: %s",
                user_identifier,
            )

            # Step 2: Get the full entity to read its relations
            entity_url = (
                f"{self._config.PORT_API_URL}/blueprints/_user/entities/{user_identifier}"
            )
            entity_response = self._port_session.get(entity_url, timeout=TIMEOUT)
            entity_response.raise_for_status()

            user_entity = entity_response.json().get("entity", {})

            team_identifiers = user_entity.get(self._config.PORT_USER_TEAM_PROPERTY)

            # Distinguish between a missing key (None) and an empty list
            if team_identifiers is not None:
                self.logger.info(
                    "Found user '%s' with team identifiers '%s'",
                    email,
                    team_identifiers,
                )
                return team_identifiers

            self.logger.warning(
                "User '%s' found in Port but has no teams assigned.", email
            )
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error("API call failed when getting user team. Error: %s", e)
            return None

    def get_port_team_identifier(self, _team_title):
        """
        This function is no longer needed as we get identifiers directly from user relations.
        Kept here to avoid breaking imports, but it should not be called.
        """
        self.logger.warning(
            "get_port_team_identifier is deprecated and should not be used."
        )

    def update_port_repository_team(self, repo_name, team_identifier):
        """
        Updates a repository entity in Port, creating a relation to a team.
        """
        self._get_port_token()

        # Construct the prefix to remove (e.g., "my-org/")
        prefix_to_remove = f"{self._config.GITHUB_ORG}/"
        if repo_name.startswith(prefix_to_remove):
            clean_repo_name = repo_name[len(prefix_to_remove) :]
        else:
            clean_repo_name = repo_name

        self.logger.info(
            "Updating Port repo '%s' with team relation '%s'",
            clean_repo_name,
            team_identifier,
        )
        entity_payload = {
            "identifier": clean_repo_name,
            "relations": {self._config.PORT_REPO_TEAM_RELATION: [team_identifier]},
        }
        try:
            url = (
                f"{self._config.PORT_API_URL}/blueprints/"
                f"{self._config.PORT_BLUEPRINT_IDENTIFIER}/entities"
            )
            response = self._port_session.post(
                url,
                params={"upsert": "true", "merge": "true"},
                json=entity_payload,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            self.logger.info(
                "Successfully upserted entity '%s' with team '%s'.",
                clean_repo_name,
                team_identifier,
            )
        except requests.exceptions.RequestException as e:
            error_message = e.response.text if e.response else str(e)
            self.logger.error(
                "API error updating Port repo %s: %s", clean_repo_name, error_message
            )

    def get_entity(self, blueprint_identifier, entity_identifier):
        """
        Fetches a single entity from Port by its blueprint and entity identifier.
        """
        self._get_port_token()
        self.logger.info(
            "Fetching Port entity '%s' from blueprint '%s'",
            entity_identifier,
            blueprint_identifier,
        )
        try:
            url = (
                f"{self._config.PORT_API_URL}/blueprints/{blueprint_identifier}"
                f"/entities/{entity_identifier}"
            )
            response = self._port_session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json().get("entity", {})
        except requests.exceptions.RequestException as e:
            err = e.response.text if e.response else str(e)
            self.logger.error(
                "API call failed when getting entity '%s': %s", entity_identifier, err
            )
            return None

    def update_entity(self, blueprint_identifier, entity_identifier, payload):
        """
        Updates a single entity in Port with the given payload.
        Uses PATCH for partial updates.
        """
        self._get_port_token()
        self.logger.info(
            "Updating Port entity '%s' in blueprint '%s'",
            entity_identifier,
            blueprint_identifier,
        )
        try:
            url = (
                f"{self._config.PORT_API_URL}/blueprints/{blueprint_identifier}"
                f"/entities/{entity_identifier}"
            )
            response = self._port_session.patch(url, json=payload, timeout=TIMEOUT)
            response.raise_for_status()
            self.logger.info("Successfully updated entity '%s'.", entity_identifier)
            return True
        except requests.exceptions.RequestException as e:
            err = e.response.text if e.response else str(e)
            self.logger.error(
                "API error updating Port entity %s: %s", entity_identifier, err
            )
            return False

    def get_all_entities_for_blueprint(self, blueprint_identifier):
        """
        Fetches all entities for a given blueprint.
        """
        self._get_port_token()
        self.logger.info(
            "Fetching all Port entities for blueprint '%s'", blueprint_identifier
        )
        try:
            url = (
                f"{self._config.PORT_API_URL}/blueprints/{blueprint_identifier}/entities"
            )
            response = self._port_session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json().get("entities", [])
        except requests.exceptions.RequestException as e:
            err = e.response.text if e.response else str(e)
            self.logger.error(
                "API call failed when getting all entities for blueprint '%s': %s",
                blueprint_identifier,
                err,
            )
            return []
