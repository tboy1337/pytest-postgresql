"""Noproc fixture tests."""

import os
import pathlib

import pytest
from psycopg import Connection

import pytest_postgresql.factories.client
import pytest_postgresql.factories.noprocess
from tests.loader import load_database

# Read environment variables for Docker or default to localhost for native tests
DOCKER_HOST = os.environ.get("POSTGRESQL_HOST", "localhost")
DOCKER_PORT = int(os.environ.get("POSTGRESQL_PORT", "5433"))
DOCKER_USER = os.environ.get("POSTGRESQL_USER", "postgres")
DOCKER_PASSWORD = os.environ.get("POSTGRESQL_PASSWORD", "postgres")

postgresql_my_proc = pytest_postgresql.factories.noprocess.postgresql_noproc(
    host=DOCKER_HOST,
    port=DOCKER_PORT,
    user=DOCKER_USER,
    password=DOCKER_PASSWORD,
    load=[pathlib.Path("tests/test_sql/eidastats.sql")]
)
postgres_with_schema = pytest_postgresql.factories.client.postgresql("postgresql_my_proc")

postgresql_my_proc_template = pytest_postgresql.factories.noprocess.postgresql_noproc(
    host=DOCKER_HOST,
    port=DOCKER_PORT,
    user=DOCKER_USER,
    password=DOCKER_PASSWORD,
    dbname="docker_stories_templated",
    load=[load_database]
)
postgres_with_template = pytest_postgresql.factories.client.postgresql(
    "postgresql_my_proc_template", dbname="docker_stories_templated"
)


def test_postgres_docker_load(postgres_with_schema: Connection) -> None:
    """Check main postgres fixture."""
    with postgres_with_schema.cursor() as cur:
        # Query for public.tokens since the eidastats changes postgres' search_path to ''.
        # The search path by default is public, but without it,
        # every schema has to be written explicitly.
        cur.execute("select * from public.tokens")
        print(cur.fetchall())


@pytest.mark.parametrize("_", range(5))
def test_template_database(postgres_with_template: Connection, _: int) -> None:
    """Check that the database structure gets recreated out of a template."""
    with postgres_with_template.cursor() as cur:
        cur.execute("SELECT * FROM stories")
        res = cur.fetchall()
        assert len(res) == 4
        cur.execute("TRUNCATE stories")
        cur.execute("SELECT * FROM stories")
        res = cur.fetchall()
        assert len(res) == 0
