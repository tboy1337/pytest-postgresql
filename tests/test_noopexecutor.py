"""Test for NoopExecutor."""

import shutil
from typing import Any
from unittest.mock import MagicMock, patch

import psycopg
import pytest
from packaging.version import Version

from pytest_postgresql.executor import PostgreSQLExecutor
from pytest_postgresql.executor_noop import NoopExecutor
from pytest_postgresql.retry import retry


@pytest.mark.skipif(
    not shutil.which("pg_ctl"),
    reason="Requires pg_ctl - run via Docker: docker-compose -f docker-compose.tests.yml up"
)
def test_noproc_version(postgresql_proc: PostgreSQLExecutor) -> None:
    """Test the way postgresql version is being read.

    Version behaves differently for postgresql >= 10 and differently for older ones
    """
    postgresql_noproc = NoopExecutor(
        postgresql_proc.host,
        postgresql_proc.port,
        postgresql_proc.user,
        postgresql_proc.options,
        postgresql_proc.dbname,
    )
    noproc_version = retry(
        lambda: postgresql_noproc.version,
        possible_exception=psycopg.OperationalError,
    )
    assert postgresql_proc.version == noproc_version


@pytest.mark.skipif(
    not shutil.which("pg_ctl"),
    reason="Requires pg_ctl - run via Docker: docker-compose -f docker-compose.tests.yml up"
)
def test_noproc_cached_version(postgresql_proc: PostgreSQLExecutor) -> None:
    """Test that the version is being cached."""
    postgresql_noproc = NoopExecutor(
        postgresql_proc.host,
        postgresql_proc.port,
        postgresql_proc.user,
        postgresql_proc.options,
        postgresql_proc.dbname,
    )
    ver = retry(
        lambda: postgresql_noproc.version,
        possible_exception=psycopg.OperationalError,
    )
    with postgresql_proc.stopped():
        assert ver == postgresql_noproc.version


def test_noop_executor_init() -> None:
    """Test NoopExecutor initialization."""
    executor = NoopExecutor(
        host="localhost",
        port="5432",
        user="testuser",
        options="-c log_statement=all",
        dbname="testdb",
        password="testpass",
    )
    assert executor.host == "localhost"
    assert executor.port == 5432  # Should be converted to int
    assert executor.user == "testuser"
    assert executor.options == "-c log_statement=all"
    assert executor.dbname == "testdb"
    assert executor.password == "testpass"
    assert executor._version is None


def test_noop_executor_init_with_int_port() -> None:
    """Test NoopExecutor initialization with integer port."""
    executor = NoopExecutor(
        host="localhost",
        port=5433,
        user="testuser",
        options="",
        dbname="testdb",
    )
    assert executor.port == 5433


def test_noop_executor_init_without_password() -> None:
    """Test NoopExecutor initialization without password."""
    executor = NoopExecutor(
        host="localhost",
        port="5432",
        user="testuser",
        options="",
        dbname="testdb",
    )
    assert executor.password is None


def test_noop_executor_template_dbname() -> None:
    """Test template_dbname property."""
    executor = NoopExecutor(
        host="localhost",
        port="5432",
        user="testuser",
        options="",
        dbname="mydb",
    )
    assert executor.template_dbname == "mydb_tmpl"


def test_noop_executor_template_dbname_various_names() -> None:
    """Test template_dbname with various database names."""
    test_cases = [
        ("testdb", "testdb_tmpl"),
        ("db_name", "db_name_tmpl"),
        ("123", "123_tmpl"),
        ("", "_tmpl"),
    ]
    for dbname, expected in test_cases:
        executor = NoopExecutor(
            host="localhost",
            port="5432",
            user="testuser",
            options="",
            dbname=dbname,
        )
        assert executor.template_dbname == expected


@patch("pytest_postgresql.executor_noop.psycopg.connect")
def test_noop_executor_version_postgresql_10_plus(mock_connect: Any) -> None:
    """Test version parsing for PostgreSQL 10+."""
    # PostgreSQL 10+ has 6-digit version
    mock_connection = MagicMock()
    mock_connection.info.server_version = 100018  # PostgreSQL 10.18
    mock_connect.return_value.__enter__.return_value = mock_connection

    executor = NoopExecutor(
        host="localhost",
        port="5432",
        user="testuser",
        options="",
        dbname="testdb",
        password="testpass",
    )

    version = executor.version
    assert isinstance(version, Version)
    assert str(version) == "10.18"

    # Verify connection was called with correct parameters
    mock_connect.assert_called_once_with(
        dbname="postgres",
        user="testuser",
        host="localhost",
        port=5432,
        password="testpass",
        options="",
    )


@patch("pytest_postgresql.executor_noop.psycopg.connect")
def test_noop_executor_version_postgresql_9(mock_connect: Any) -> None:
    """Test version parsing for PostgreSQL 9.x."""
    # PostgreSQL 9.x has 5-digit version, needs padding
    mock_connection = MagicMock()
    mock_connection.info.server_version = 90624  # PostgreSQL 9.6.24
    mock_connect.return_value.__enter__.return_value = mock_connection

    executor = NoopExecutor(
        host="localhost",
        port="5432",
        user="testuser",
        options="",
        dbname="testdb",
    )

    version = executor.version
    assert isinstance(version, Version)
    # Version should be padded and parsed
    assert str(version) == "9.6"


@patch("pytest_postgresql.executor_noop.psycopg.connect")
def test_noop_executor_version_postgresql_11(mock_connect: Any) -> None:
    """Test version parsing for PostgreSQL 11."""
    mock_connection = MagicMock()
    mock_connection.info.server_version = 110013  # PostgreSQL 11.13
    mock_connect.return_value.__enter__.return_value = mock_connection

    executor = NoopExecutor(
        host="localhost",
        port="5432",
        user="testuser",
        options="",
        dbname="testdb",
    )

    version = executor.version
    assert isinstance(version, Version)
    assert str(version) == "11.13"


@patch("pytest_postgresql.executor_noop.psycopg.connect")
def test_noop_executor_version_postgresql_14(mock_connect: Any) -> None:
    """Test version parsing for PostgreSQL 14."""
    mock_connection = MagicMock()
    mock_connection.info.server_version = 140000  # PostgreSQL 14.0
    mock_connect.return_value.__enter__.return_value = mock_connection

    executor = NoopExecutor(
        host="localhost",
        port="5432",
        user="testuser",
        options="",
        dbname="testdb",
    )

    version = executor.version
    assert isinstance(version, Version)
    # Version 14.0 with all zeros filtered out becomes just "14"
    assert str(version) == "14"


@patch("pytest_postgresql.executor_noop.psycopg.connect")
def test_noop_executor_version_cached(mock_connect: Any) -> None:
    """Test that version is cached after first access."""
    mock_connection = MagicMock()
    mock_connection.info.server_version = 120008
    mock_connect.return_value.__enter__.return_value = mock_connection

    executor = NoopExecutor(
        host="localhost",
        port="5432",
        user="testuser",
        options="",
        dbname="testdb",
    )

    # First access
    version1 = executor.version
    # Second access should use cached value
    version2 = executor.version

    assert version1 == version2
    # Connection should only be called once
    assert mock_connect.call_count == 1


@patch("pytest_postgresql.executor_noop.psycopg.connect")
def test_noop_executor_version_with_zero_parts(mock_connect: Any) -> None:
    """Test version parsing with zero parts (e.g., 10.0)."""
    mock_connection = MagicMock()
    mock_connection.info.server_version = 100000  # PostgreSQL 10.0
    mock_connect.return_value.__enter__.return_value = mock_connection

    executor = NoopExecutor(
        host="localhost",
        port="5432",
        user="testuser",
        options="",
        dbname="testdb",
    )

    version = executor.version
    assert isinstance(version, Version)
    # Zero parts should be filtered out per the code logic
    assert str(version) == "10"


@patch("pytest_postgresql.executor_noop.psycopg.connect")
def test_noop_executor_version_connection_error(mock_connect: Any) -> None:
    """Test version property when connection fails."""
    mock_connect.side_effect = psycopg.OperationalError("Connection refused")

    executor = NoopExecutor(
        host="localhost",
        port="5432",
        user="testuser",
        options="",
        dbname="testdb",
    )

    with pytest.raises(psycopg.OperationalError):
        _ = executor.version
