"""
This module contains an integration test to verify the retrieval of user team
identifiers from the Port API.

It is designed to be run manually to test the connection and data retrieval
against a live Port instance.

Pylint disable justifications:
- broad-exception-caught: A broad exception is caught to log any unexpected
  failure during the integration test run, which is acceptable for this
  manual test script.
"""
from repo_team_mapper import config
from repo_team_mapper.api_client import ApiClient

def test_user_team_identifier_retrieval():
    """
    A targeted test to verify that we can correctly retrieve the team IDENTIFIERS
    for a specific user from Port.
    """
    main_logger, _ = config.setup_logging()
    main_logger.info("--- Starting User Team Identifier Retrieval Test ---")
    print("Running test to find team identifiers for a known user...")

    try:
        api_client = ApiClient(config)

        # --- IMPORTANT ---
        # Please change this email to a real user in your Port instance
        # that you know is assigned to one or more teams.
        email_to_test = "jordan.thomas@fortescue.com"

        main_logger.info(
            "Attempting to find team identifiers for user: '%s'", email_to_test
        )

        # Call the specific function we want to test
        team_identifiers = api_client.get_port_user_team(email_to_test)

        if team_identifiers and isinstance(team_identifiers, list):
            print(f"✅ SUCCESS: Found team identifiers: {team_identifiers}")
            # Example check:
            if "group-technology" in team_identifiers:
                print("✅ Found 'group-technology' as expected.")
            if "super_users" in team_identifiers:
                print("✅ Found 'super_users' as expected.")

        elif team_identifiers is None:
            print(
                f"❌ FAILURE: The user '{email_to_test}' was not found or has no teams assigned."
            )

        else:
            print(
                "❌ UNEXPECTED RESULT: The function returned something other than a "
                f"list or None: {team_identifiers}"
            )

    except Exception as e:  # pylint: disable=broad-exception-caught
        main_logger.critical(
            "A critical error occurred during the test: %s", e, exc_info=True
        )
        print(f"❌ TEST FAILED with critical error: {e}")
    finally:
        main_logger.info("--- Test Finished ---")
        print("\nTest complete. Check mapping.log for detailed API call information.")

if __name__ == "__main__":
    test_user_team_identifier_retrieval()
