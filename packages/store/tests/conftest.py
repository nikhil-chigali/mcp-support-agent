"""Shared fixtures. Database tests run against store_test, which may be wiped."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

TEST_DATABASE_URL = os.environ.get(
    "STORE_TEST_DATABASE_URL",
    "postgresql+psycopg://store_app:store_app@localhost:5432/store_test",
)
STORE_PACKAGE = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def test_engine():
    """An engine on store_test, migrated to head.

    Without Postgres the database tests are skipped, so `just test` still works
    with the container down. CI sets STORE_REQUIRE_DB=1 to make that a failure
    instead: a skipped test there would hide a broken database step.
    """
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect():
            pass
    except OperationalError:
        if os.environ.get("STORE_REQUIRE_DB"):
            raise
        pytest.skip("store_test is not reachable; run `just up`")

    # A subprocess, because alembic's env.py reads STORE_DATABASE_URL at import.
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=STORE_PACKAGE,
        env={**os.environ, "STORE_DATABASE_URL": TEST_DATABASE_URL},
        check=True,
        capture_output=True,
    )
    yield engine
    engine.dispose()
