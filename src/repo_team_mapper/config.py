"""
This module loads and validates all configuration settings for the application
from environment variables. It also configures the loggers.
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- GitHub Configuration ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_ORG = os.getenv("GITHUB_ORG")

# --- Port Configuration ---
PORT_CLIENT_ID = os.getenv("PORT_CLIENT_ID")
PORT_CLIENT_SECRET = os.getenv("PORT_CLIENT_SECRET")
# The base URL for the Port API
PORT_API_URL = os.getenv("PORT_API_URL", "https://api.getport.io/v1")

# --- Script Configuration ---
# Number of top committers to analyze for each repository
TOP_COMMITTERS_COUNT = int(os.getenv("TOP_COMMITTERS_COUNT", "5"))
# The identifier of the Port blueprint for your repositories (e.g., "service", "repository")
PORT_BLUEPRINT_IDENTIFIER = os.getenv("PORT_BLUEPRINT_IDENTIFIER", "service")
# The identifier of the relation on the repository blueprint that links to the team
PORT_REPO_TEAM_RELATION = os.getenv("PORT_REPO_TEAM_RELATION", "team")
# The property on the Port User entity that holds their team identifier(s)
PORT_USER_TEAM_PROPERTY = os.getenv("PORT_USER_TEAM_PROPERTY", "team")

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "mapper.log"
UNMAPPED_LOG_FILE = "unmapped_repos.log"

# Concurrency and State
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "10"))  # Number of parallel threads to run
STATE_FILE = "repos_to_process.txt"  # File to store the list of repos to be processed

# Basic validation
if not all([GITHUB_TOKEN, GITHUB_ORG, PORT_CLIENT_ID, PORT_CLIENT_SECRET]):
    raise ValueError("One or more required environment variables are missing.")

def setup_logging(log_file=LOG_FILE, unmapped_log_file=UNMAPPED_LOG_FILE, log_level=LOG_LEVEL):
    """Configures the main and unmapped repositories loggers."""
    # Main logger
    log_format = "%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    # Unmapped repositories logger
    unmapped_logger = logging.getLogger('unmapped_logger')
    unmapped_logger.setLevel(logging.INFO)
    # Prevent unmapped logs from propagating to the main logger
    unmapped_logger.propagate = False

    # Add a handler for the unmapped log file if not already present
    if not unmapped_logger.handlers:
        unmapped_handler = logging.FileHandler(unmapped_log_file)
        unmapped_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        unmapped_logger.addHandler(unmapped_handler)

    return logging.getLogger(__name__), unmapped_logger
