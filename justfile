# Run `just` to list recipes.

# Throwaway database for migration checks; `downgrade base` drops every table.
store_test_url := "postgresql+psycopg://store_app:store_app@localhost:5432/store_test"

default:
    @just --list

# --- Database ---------------------------------------------------------------

# Start Postgres in the background and wait until it is healthy
up:
    docker compose up -d --wait

# Stop Postgres (data is kept in the volume)
down:
    docker compose down

# Delete the database volume and start fresh; re-runs the init script
[confirm("This deletes ALL local database data. Continue? (y/N)")]
reset-db:
    docker compose down -v
    docker compose up -d --wait
    just migrate

# Open psql inside the container, e.g. `just psql store_test`
psql db="store":
    docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d {{db}}'

# Apply all migrations to the dev database
migrate:
    cd packages/store && uv run alembic upgrade head

# Wipe the dev database and load the seed world; prints where each scenario landed
seed:
    cd packages/store && uv run python -m store.seed

# Prove migrations match the models and downgrade cleanly (runs on store_test only)
migration-check:
    cd packages/store && STORE_DATABASE_URL={{store_test_url}} uv run alembic downgrade base
    cd packages/store && STORE_DATABASE_URL={{store_test_url}} uv run alembic upgrade head
    cd packages/store && STORE_DATABASE_URL={{store_test_url}} uv run alembic check
    cd packages/store && STORE_DATABASE_URL={{store_test_url}} uv run alembic downgrade base
    cd packages/store && STORE_DATABASE_URL={{store_test_url}} uv run alembic upgrade head

# --- Code -------------------------------------------------------------------

# Lint, check formatting, and enforce the package boundaries
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run lint-imports

# Auto-format and apply safe lint fixes
fmt:
    uv run ruff format .
    uv run ruff check --fix .

# Run tests; extra args go to pytest, e.g. `just test -k refund`
test *args:
    uv run pytest packages {{args}}
