"""Template database tests."""

import os

import pytest
from psycopg import Connection

from pytest_postgresql.factories import postgresql, postgresql_noproc
from tests.loader import load_database

# Docker-based fixtures for cross-platform compatibility
DOCKER_HOST = os.environ.get("POSTGRESQL_HOST", "localhost")
DOCKER_PORT = int(os.environ.get("POSTGRESQL_PORT", "5433"))
DOCKER_USER = os.environ.get("POSTGRESQL_USER", "postgres")
DOCKER_PASSWORD = os.environ.get("POSTGRESQL_PASSWORD", "postgres")

postgresql_proc_with_template = postgresql_noproc(
    host=DOCKER_HOST,
    port=DOCKER_PORT,
    user=DOCKER_USER,
    password=DOCKER_PASSWORD,
    dbname="stories_templated",
    load=[load_database],
)

postgresql_template = postgresql(
    "postgresql_proc_with_template",
    dbname="stories_templated",
)


@pytest.mark.xdist_group(name="template_database")
@pytest.mark.parametrize("_", range(5))
def test_template_database(postgresql_template: Connection, _: int) -> None:
    """Check that the database structure gets recreated out of a template."""
    with postgresql_template.cursor() as cur:
        cur.execute("SELECT * FROM stories")
        res = cur.fetchall()
        assert len(res) == 4
        cur.execute("TRUNCATE stories")
        cur.execute("SELECT * FROM stories")
        res = cur.fetchall()
        assert len(res) == 0
