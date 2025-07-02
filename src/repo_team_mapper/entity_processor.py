"""
This script provides a utility to migrate team data from a relation-based
property to a simple string/list-of-strings property on any given blueprint.

It is designed to be run as a one-off utility to backfill data after a
model change in Port.
"""
import logging
from .api_client import ApiClient

# As this is a utility class, having only one public method is acceptable.
# pylint: disable=too-few-public-methods
class EntityTeamMigrator:
    """A utility to migrate team data from a relation to a property."""

    def __init__(self, config_obj):
        self.logger = logging.getLogger(__name__)
        self.api_client = ApiClient(config_obj)
        self.config = config_obj

    def migrate_team_relations(self, blueprint_identifier):
        """
        Fetches all entities for a blueprint, reads the team relation,
        and patches the entity with the new team property.
        """
        self.logger.info(
            "Starting team migration for blueprint: '%s'", blueprint_identifier
        )
        entities = self.api_client.get_all_entities_for_blueprint(
            blueprint_identifier
        )

        if not entities:
            self.logger.warning(
                "No entities found for blueprint '%s'. Nothing to migrate.",
                blueprint_identifier,
            )
            return

        for entity in entities:
            entity_identifier = entity["identifier"]
            self.logger.info("Processing entity: '%s'", entity_identifier)

            # Fetch the full entity to get its relations
            full_entity = self.api_client.get_entity(
                blueprint_identifier, entity_identifier
            )
            if not full_entity:
                self.logger.error(
                    "Could not fetch full details for entity '%s'. Skipping.",
                    entity_identifier,
                )
                continue

            try:
                # Extract team identifiers from the relation
                team_relation_data = full_entity.get("relations", {}).get(
                    self.config.PORT_REPO_TEAM_RELATION
                )

                if not team_relation_data:
                    self.logger.warning(
                        "Entity '%s' has no team relation data. Skipping.",
                        entity_identifier,
                    )
                    continue

                # The relation can be a string or a list
                team_identifiers = (
                    team_relation_data
                    if isinstance(team_relation_data, list)
                    else [team_relation_data]
                )

                self.logger.info(
                    "Found team identifiers '%s' for entity '%s'.",
                    team_identifiers,
                    entity_identifier,
                )

                # Prepare payload for the new multi-select property
                payload = {"properties": {self.config.PORT_USER_TEAM_PROPERTY: team_identifiers}}
                self.api_client.update_entity(
                    blueprint_identifier, entity_identifier, payload
                )

            # A broad exception is caught here to ensure one failed entity
            # doesn't stop the entire migration process.
            # pylint: disable=broad-exception-caught
            except Exception as e:
                self.logger.error(
                    "An unexpected error occurred while processing entity '%s': %s",
                    entity_identifier,
                    e,
                )
        self.logger.info(
            "Finished team migration for blueprint: '%s'", blueprint_identifier
        )
