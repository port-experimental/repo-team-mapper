"""
This module contains the RepoProcessor class, which encapsulates the logic
for processing a single repository: fetching its data, analyzing committers,
and updating its ownership in Port.
"""
import logging
import threading

# As this is a focused utility class, having only one public method is acceptable.
# pylint: disable=too-few-public-methods
class RepoProcessor:
    """Handles the processing for a single repository."""

    def __init__(self, api_client, config_obj, unmapped_logger):
        self.api_client = api_client
        self.config = config_obj
        self.logger = logging.getLogger(__name__)
        self.unmapped_logger = unmapped_logger

    def process_repo(self, repo_name):
        """
        Processes a single repository to determine and update its team ownership.
        """
        thread_name = threading.current_thread().name
        self.logger.info("[%s] Processing repo: %s", thread_name, repo_name)

        repo = self.api_client.get_repo(repo_name)
        if not repo:
            self.logger.error("[%s] Could not retrieve repo object for %s.", thread_name, repo_name)
            return

        committers = self.api_client.get_top_committers(repo)
        if not committers:
            self.logger.warning(
                "[%s] No committers found for repo %s. Skipping.", thread_name, repo_name
            )
            self.unmapped_logger.info(
                "%s - No committers with public emails found.", repo_name
            )
            return

        # Find the first committer who is part of a team in Port
        for committer in committers:
            committer_email = committer.get("email")
            if not committer_email:
                continue

            self.logger.info(
                "[%s] Checking committer '%s' for teams...", thread_name, committer_email
            )
            teams = self.api_client.get_port_user_team(committer_email)

            if teams:
                team_identifier = teams[0]  # Take the first team for simplicity
                self.logger.info(
                    "[%s] Found team '%s' for committer '%s'. Updating Port.",
                    thread_name,
                    team_identifier,
                    committer_email,
                )
                self.api_client.update_port_repository_team(repo_name, team_identifier)
                return  # Stop after the first successful mapping

        # If no committers were mapped to a team
        self.logger.warning(
            "[%s] No mapped teams found for any top committer in repo %s.",
            thread_name,
            repo_name,
        )
        self.unmapped_logger.info(
            "%s - No committers found belonging to a Port team.", repo_name
        )
