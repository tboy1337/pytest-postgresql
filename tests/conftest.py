"""Tests main conftest file."""

import os
from pathlib import Path

from pytest_postgresql import factories

pytest_plugins = ["pytester"]
POSTGRESQL_VERSION = os.environ.get("POSTGRES", "13")


TEST_SQL_DIR = os.path.dirname(os.path.abspath(__file__)) + "/test_sql/"
TEST_SQL_FILE = Path(TEST_SQL_DIR + "test.sql")
TEST_SQL_FILE2 = Path(TEST_SQL_DIR + "test2.sql")

# Docker-based fixtures for cross-platform compatibility
# Use environment variables or defaults for Docker PostgreSQL
DOCKER_HOST = os.environ.get("POSTGRESQL_HOST", "localhost")
DOCKER_PORT = int(os.environ.get("POSTGRESQL_PORT", "5433"))
DOCKER_USER = os.environ.get("POSTGRESQL_USER", "postgres")
DOCKER_PASSWORD = os.environ.get("POSTGRESQL_PASSWORD", "postgres")

# Default noproc fixture connecting to Docker
postgresql_noproc = factories.postgresql_noproc(
    host=DOCKER_HOST,
    port=DOCKER_PORT,
    user=DOCKER_USER,
    password=DOCKER_PASSWORD,
    dbname="tests_default",  # Unique dbname to avoid template conflicts
)

# Default postgresql client fixture
postgresql = factories.postgresql("postgresql_noproc")

# Use postgresql_noproc to connect to Docker container instead of postgresql_proc
postgresql_proc2 = factories.postgresql_noproc(
    host=DOCKER_HOST,
    port=DOCKER_PORT,
    user=DOCKER_USER,
    password=DOCKER_PASSWORD,
    dbname="tests_proc2",  # Unique dbname to avoid template conflicts
    load=[TEST_SQL_FILE, TEST_SQL_FILE2],
)
postgresql2 = factories.postgresql("postgresql_proc2", dbname="test-db")
postgresql_load_1 = factories.postgresql("postgresql_proc2")
