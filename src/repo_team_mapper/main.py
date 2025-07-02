"""
This is the main entry point for the repository-to-team mapping script.

It initializes the necessary clients and services, manages the processing
of repositories in parallel, and handles state to ensure that repositories
are not processed repeatedly.
"""
import concurrent.futures
import logging
import os
import sys

from . import config
from .api_client import ApiClient
from .processor import RepoProcessor

# A broad exception is caught at the thread level to prevent one failure
# from stopping the entire processing run.
# pylint: disable=broad-exception-caught


def process_repo_wrapper(repo_processor, repo_name):
    """
    A wrapper to call the process_repo method, designed to be used by the
    ThreadPoolExecutor. It logs exceptions that occur within a thread.
    """
    try:
        repo_processor.process_repo(repo_name)
    except Exception as e:
        logging.error(
            "An unexpected error occurred in worker thread for repo %s: %s",
            repo_name,
            e,
            exc_info=True,
        )


def load_repositories_to_process(state_file, api_client):
    """
    Loads the list of repositories to process. If the state file exists,
    it reads from there. Otherwise, it fetches all repositories from the API
    and populates the state file.
    """
    if os.path.exists(state_file):
        logging.info("Continuing from existing state file: %s", state_file)
        with open(state_file, "r", encoding="utf-8") as f:
            # Filter out empty lines that might exist
            return [line.strip() for line in f if line.strip()]

    logging.info("No state file found. Fetching all organization repositories.")
    try:
        all_repos = api_client.get_all_organization_repos()
        repo_names = [repo.full_name for repo in all_repos]

        with open(state_file, "w", encoding="utf-8") as f:
            for repo_name in repo_names:
                f.write(f"{repo_name}\n")
        logging.info(
            "Created state file with %d repositories.", len(repo_names)
        )
        return repo_names
    except Exception as e:
        logging.error("Failed to fetch and create initial repo list: %s", e)
        return []


def main():
    """Main function to run the repository processing."""
    # Initialize logging and configuration
    cfg = config
    logger, unmapped_logger = cfg.setup_logging()

    api_client = ApiClient(cfg)
    repo_processor = RepoProcessor(api_client, cfg, unmapped_logger)

    # Load the list of repositories
    repos_to_process = load_repositories_to_process(cfg.STATE_FILE, api_client)
    if not repos_to_process:
        logger.error("No repositories to process. Exiting.")
        sys.exit(1)

    logger.info("--- Starting repository processing run ---")
    logger.info("Found %d repositories to process.", len(repos_to_process))

    # Use a ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.MAX_WORKERS) as executor:
        # Create a future for each repository to be processed
        futures = [
            executor.submit(process_repo_wrapper, repo_processor, repo_name)
            for repo_name in repos_to_process
        ]
        concurrent.futures.wait(futures)

    logger.info("--- Repository processing run finished ---")
    # Clean up the state file after a successful run
    if os.path.exists(cfg.STATE_FILE):
        logger.info("Processing complete. Deleting state file: %s.", cfg.STATE_FILE)
        os.remove(cfg.STATE_FILE)
    else:
        logger.info("Processing complete. No state file to delete.")

if __name__ == "__main__":
    main()
