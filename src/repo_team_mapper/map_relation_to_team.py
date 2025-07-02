"""
This script is the entry point for the one-off utility to migrate team data
from a Port relation to a multi-select property.

It takes a blueprint identifier as a command-line argument and processes
all entities within that blueprint.
"""
import sys

from . import config
from .entity_processor import EntityTeamMigrator

# A broad exception is caught to ensure that any unexpected error during
# the setup or execution is logged before the script exits.
# pylint: disable=broad-exception-caught
def main():
    """
    Main function to run the entity team migration.
    Expects the blueprint identifier as a command-line argument.
    """
    # 1. Setup Logging
    logger, _ = config.setup_logging(
        log_file="entity_migration.log", unmapped_log_file="unused.log"
    )
    logger.info("--- Starting Entity Team Migration Script ---")

    # 2. Argument validation
    if len(sys.argv) < 2:
        logger.critical("Blueprint identifier must be provided as an argument.")
        logger.critical("Usage: poetry run entity-team-mapper <blueprint_identifier>")
        sys.exit(1)

    blueprint_identifier = sys.argv[1]
    logger.info("Targeting blueprint: '%s'", blueprint_identifier)

    try:
        # 3. Initialize and run the migrator
        migrator = EntityTeamMigrator(config)
        migrator.migrate_team_relations(blueprint_identifier)

    except Exception as e:
        logger.critical(
            "A critical error occurred during the migration process: %s", e, exc_info=True
        )
        sys.exit(1)

    logger.info("--- Entity Team Migration Script Finished ---")


if __name__ == "__main__":
    main()
