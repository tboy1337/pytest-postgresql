"""Test client factory module."""

import pytest

from pytest_postgresql.factories import client


def test_postgresql_returns_fixture() -> None:
    """Test postgresql returns a fixture function."""
    result = client.postgresql("postgresql_proc")

    assert callable(result)
    # The function returned is wrapped by pytest.fixture decorator
    assert hasattr(result, "__wrapped__") or hasattr(result, "_pytestfixturefunction")


def test_postgresql_with_custom_dbname() -> None:
    """Test postgresql with custom database name."""
    result = client.postgresql("postgresql_proc", dbname="customdb")

    assert callable(result)


def test_postgresql_with_isolation_level() -> None:
    """Test postgresql with isolation level."""
    import psycopg

    result = client.postgresql(
        "postgresql_proc",
        isolation_level=psycopg.IsolationLevel.SERIALIZABLE,
    )

    assert callable(result)


def test_postgresql_with_all_parameters() -> None:
    """Test postgresql with all parameters."""
    import psycopg

    result = client.postgresql(
        "postgresql_proc",
        dbname="testdb",
        isolation_level=psycopg.IsolationLevel.READ_COMMITTED,
    )

    assert callable(result)


def test_postgresql_with_different_process_fixture_names() -> None:
    """Test postgresql with different process fixture names."""
    fixtures = [
        "postgresql_proc",
        "postgresql_noproc",
        "custom_postgresql",
        "pg_proc",
    ]

    for fixture_name in fixtures:
        result = client.postgresql(fixture_name)
        assert callable(result)


def test_postgresql_with_noproc_fixture() -> None:
    """Test postgresql can work with noproc fixture."""
    result = client.postgresql("postgresql_noproc")
    assert callable(result)


def test_postgresql_default_parameters() -> None:
    """Test postgresql with default parameters."""
    result = client.postgresql("postgresql_proc")

    assert callable(result)
