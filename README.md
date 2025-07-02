# Repository Team Mapper for Port

This project contains two primary tools to automate repository and entity management in your [Port](https://getport.io) software catalog.

1.  **Repository Team Mapper**: Maps repositories to the teams that own them by analyzing commit history.
2.  **Entity Team Mapper**: A utility script to migrate team data from a `relation` to a top-level `team` property on any given entity blueprint.

This is ideal for organizations looking to automatically populate and maintain ownership data, reducing manual effort and keeping the catalog up-to-date.

## How It Works

### 1. Repository Team Mapper (`repo_team_mapper`)

This is the main script for automated ownership mapping.

1.  **Fetches Repositories**: The script gets a list of all repositories in your specified GitHub organization.
2.  **Manages State**: It keeps track of which repositories have been processed in a state file (`repos_to_process.txt`), allowing it to be stopped and restarted without losing progress.
3.  **Analyzes Committers**: For each repository, it fetches the list of top committers based on their number of commits.
4.  **Finds User in Port**: It searches for the top committers in your Port catalog by their email address.
5.  **Assigns Team**: The first committer found who belongs to a team in Port will have their team assigned to the repository entity.
6.  **Updates Port**: The script creates or updates the repository entity in Port, creating a relation to the appropriate team entity.

### 2. Entity Team Mapper (`map_relation_to_team`)

This is a utility script designed for data migration. If you previously stored team ownership in a `relation` and now want to move it to a multi-select `team` property on your entities, this script automates that process.

- It fetches all entities for a specified blueprint.
- For each entity, it reads the team identifier(s) from the `relations.team` field.
- It then updates the entity, populating the top-level `team` property with those same identifiers.

## Prerequisites

- Python 3.8+
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management.
- A GitHub Personal Access Token with `repo` scope.
- A Port API Client ID and Secret with read/write permissions.

## Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd repo-team-mapper
    ```

2.  **Install Dependencies:**
    This project uses Poetry to manage its dependencies. Poetry will automatically create and manage a virtual environment.
    ```bash
    poetry install
    ```
    To include the development dependencies (like `pytest`), run:
    ```bash
    poetry install --with dev
    ```

3.  **Configure Environment Variables:**
    Create a file named `.env` in the root of the project. You can copy the example `.env.sample` if one exists, or create one from scratch. Then, fill in the required values.

    ```env
    # -----------------------------------------------------------------------------
    # REQUIRED: These variables must be set for the script to function.
    # -----------------------------------------------------------------------------

    # --- GitHub Configuration ---
    # Your GitHub Personal Access Token with 'repo' scope.
    GITHUB_TOKEN=""
    # The name of your GitHub organization.
    GITHUB_ORG=""

    # --- Port Configuration ---
    # Your Port API Client ID.
    PORT_CLIENT_ID=""
    # Your Port API Client Secret.
    PORT_CLIENT_SECRET=""

    # -----------------------------------------------------------------------------
    # OPTIONAL: These variables have default values but can be overridden.
    # -----------------------------------------------------------------------------
    # PORT_API_URL="https://api.getport.io/v1"
    # PORT_BLUEPRINT_IDENTIFIER="service"
    # PORT_REPO_TEAM_RELATION="team"
    # PORT_USER_TEAM_PROPERTY="team"
    # TOP_COMMITTERS_COUNT="5"
    # MAX_WORKERS="2"
    # LOG_LEVEL="INFO"
    ```

## Running the Scripts

To run the scripts, use `poetry run`, which will execute the commands within the project's virtual environment.

### Running the Repository Team Mapper

This script will map GitHub repositories to Port teams based on commit history.

```bash
poetry run python -m repo_team_mapper.main
```

On its first run, it will create a `repos_to_process.txt` file populated with all repositories from your GitHub organization and begin processing them. Subsequent runs will resume from where the script left off.

### Running the Entity Team Mapper

This utility migrates team data from a `relation` to a `team` property.

```bash
poetry run python -m repo_team_mapper.map_relation_to_team --blueprint <BLUEPRINT_IDENTIFIER>
```

**Arguments:**

-   `--blueprint`: (Required) The identifier of the blueprint whose entities you want to migrate.
-   `--dry-run`: (Optional) Run the script without making any actual changes to see what updates would be performed.

**Example:**
```bash
# Perform a dry run on the 'service' blueprint
poetry run python -m repo_team_mapper.map_relation_to_team --blueprint service --dry-run

# Run the migration for real on the 'microservice' blueprint
poetry run python -m repo_team_mapper.map_relation_to_team --blueprint microservice
```

## Advanced Configuration (Optional)

You can customize the script's behavior by setting these optional environment variables in your `.env` file:

| Variable                    | Description                                                                              | Default     |
| --------------------------- | ---------------------------------------------------------------------------------------- | ----------- |
| `PORT_API_URL`              | The base URL for the Port API.                                                           | `https://api.getport.io/v1` |
| `PORT_BLUEPRINT_IDENTIFIER` | The identifier of the Port blueprint for your repositories.                              | `service`   |
| `PORT_REPO_TEAM_RELATION`   | The identifier of the relation on the repository blueprint that links to the team.       | `team`      |
| `PORT_USER_TEAM_PROPERTY`   | The property on the Port `_user` entity that holds their team identifier(s).             | `team`      |
| `TOP_COMMITTERS_COUNT`      | The number of top committers to analyze for each repository.                             | `5`         |
| `MAX_WORKERS`               | The number of parallel threads to run for processing repositories.                       | `2`         |
| `LOG_LEVEL`                 | The logging level (e.g., `INFO`, `DEBUG`, `WARNING`).                                    | `INFO`      |

---
