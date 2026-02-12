"""Database Janitor tests."""

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import parse

from pytest_postgresql.janitor import DatabaseJanitor

VERSION = parse("10")


@pytest.mark.parametrize("version", (VERSION, 10, "10"))
def test_version_cast(version: Any) -> None:
    """Test that version is cast to Version object."""
    janitor = DatabaseJanitor(user="user", host="host", port="1234", dbname="database_name", version=version)
    assert janitor.version == VERSION


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_cursor_selects_postgres_database(connect_mock: MagicMock) -> None:
    """Test that the cursor requests the postgres database."""
    janitor = DatabaseJanitor(user="user", host="host", port="1234", dbname="database_name", version=10)
    with janitor.cursor():
        connect_mock.assert_called_once_with(dbname="postgres", user="user", password=None, host="host", port="1234")


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_cursor_connects_with_password(connect_mock: MagicMock) -> None:
    """Test that the cursor requests the postgres database."""
    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="database_name",
        version=10,
        password="some_password",
    )
    with janitor.cursor():
        connect_mock.assert_called_once_with(
            dbname="postgres", user="user", password="some_password", host="host", port="1234"
        )


@pytest.mark.skipif(sys.version_info < (3, 8), reason="Unittest call_args.kwargs was introduced since python 3.8")
@pytest.mark.parametrize("load_database", ("tests.loader.load_database", "tests.loader:load_database"))
@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_populate(connect_mock: MagicMock, load_database: str) -> None:
    """Test that the cursor requests the postgres database.

    load_database tries to connect to database, which triggers mocks.
    """
    call_kwargs = {
        "host": "host",
        "port": "1234",
        "user": "user",
        "dbname": "database_name",
        "password": "some_password",
    }
    janitor = DatabaseJanitor(version=10, **call_kwargs)  # type: ignore[arg-type]
    janitor.load(load_database)
    assert connect_mock.called
    assert connect_mock.call_args.kwargs == call_kwargs


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_init_without_template(connect_mock: MagicMock) -> None:
    """Test init() creates database without template."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    connect_mock.return_value = mock_conn

    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="testdb",
        version=10,
    )

    janitor.init()

    mock_cursor.execute.assert_called_once()
    call_args = mock_cursor.execute.call_args[0][0]
    assert 'CREATE DATABASE "testdb"' in call_args
    assert "TEMPLATE" not in call_args


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_init_with_template(connect_mock: MagicMock) -> None:
    """Test init() creates database with template."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    connect_mock.return_value = mock_conn

    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="testdb",
        template_dbname="template0",
        version=10,
    )

    janitor.init()

    # Should call execute twice: terminate connections + create database
    assert mock_cursor.execute.call_count >= 1
    calls = [str(call) for call in mock_cursor.execute.call_args_list]
    assert any('CREATE DATABASE "testdb" TEMPLATE "template0"' in str(call) for call in calls)


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_init_as_template(connect_mock: MagicMock) -> None:
    """Test init() creates database as template."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    connect_mock.return_value = mock_conn

    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="testdb",
        as_template=True,
        version=10,
    )

    janitor.init()

    mock_cursor.execute.assert_called_once()
    call_args = mock_cursor.execute.call_args[0][0]
    assert "IS_TEMPLATE = true" in call_args


def test_janitor_is_template_true() -> None:
    """Test is_template() returns True when as_template is True."""
    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="testdb",
        as_template=True,
        version=10,
    )

    assert janitor.is_template() is True


def test_janitor_is_template_false() -> None:
    """Test is_template() returns False when as_template is False."""
    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="testdb",
        as_template=False,
        version=10,
    )

    assert janitor.is_template() is False


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_drop_regular_database(connect_mock: MagicMock) -> None:
    """Test drop() for regular database."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    connect_mock.return_value = mock_conn

    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="testdb",
        version=10,
    )

    janitor.drop()

    # Should call execute 3 times: disallow connections, terminate, drop
    assert mock_cursor.execute.call_count == 3
    calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
    assert any("allow_connections false" in call for call in calls)
    assert any("pg_terminate_backend" in call for call in calls)
    assert any("DROP DATABASE" in call for call in calls)


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_drop_template_database(connect_mock: MagicMock) -> None:
    """Test drop() for template database."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    connect_mock.return_value = mock_conn

    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="testdb",
        as_template=True,
        version=10,
    )

    janitor.drop()

    # Should call execute 4 times: disallow connections, terminate, alter, drop
    assert mock_cursor.execute.call_count == 4
    calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
    assert any("is_template false" in call for call in calls)
    assert any("DROP DATABASE" in call for call in calls)


def test_janitor_dont_datallowconn() -> None:
    """Test _dont_datallowconn() static method."""
    mock_cursor = MagicMock()

    DatabaseJanitor._dont_datallowconn(mock_cursor, "testdb")

    mock_cursor.execute.assert_called_once()
    call_args = mock_cursor.execute.call_args[0][0]
    assert 'ALTER DATABASE "testdb"' in call_args
    assert "allow_connections false" in call_args


def test_janitor_terminate_connection() -> None:
    """Test _terminate_connection() static method."""
    mock_cursor = MagicMock()

    DatabaseJanitor._terminate_connection(mock_cursor, "testdb")

    mock_cursor.execute.assert_called_once()
    call_args = mock_cursor.execute.call_args[0]
    assert "pg_terminate_backend" in call_args[0]
    assert "pg_stat_activity" in call_args[0]
    assert call_args[1] == ("testdb",)


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_cursor_with_custom_dbname(connect_mock: MagicMock) -> None:
    """Test cursor() with custom database name."""
    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="database_name",
        version=10,
    )

    with janitor.cursor(dbname="custom_db"):
        connect_mock.assert_called_once_with(
            dbname="custom_db",
            user="user",
            password=None,
            host="host",
            port="1234",
        )


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_cursor_sets_isolation_level(connect_mock: MagicMock) -> None:
    """Test cursor() sets isolation level."""
    mock_conn = MagicMock()
    connect_mock.return_value = mock_conn

    import psycopg

    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="database_name",
        version=10,
        isolation_level=psycopg.IsolationLevel.SERIALIZABLE,
    )

    with janitor.cursor():
        assert mock_conn.isolation_level == psycopg.IsolationLevel.SERIALIZABLE
        assert mock_conn.autocommit is True


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_cursor_closes_connection(connect_mock: MagicMock) -> None:
    """Test cursor() properly closes cursor and connection."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    connect_mock.return_value = mock_conn

    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="database_name",
        version=10,
    )

    with janitor.cursor():
        pass

    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_context_manager_init_drop(connect_mock: MagicMock) -> None:
    """Test context manager calls init and drop."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    connect_mock.return_value = mock_conn

    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="testdb",
        version=10,
    )

    with janitor:
        # Should have called init (which calls execute once)
        assert mock_cursor.execute.call_count >= 1

    # Should have called drop (which calls execute 3 times)
    assert mock_cursor.execute.call_count >= 4


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_context_manager_returns_self(connect_mock: MagicMock) -> None:
    """Test context manager returns self."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    connect_mock.return_value = mock_conn

    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="testdb",
        version=10,
    )

    with janitor as j:
        assert j is janitor


@patch("pytest_postgresql.janitor.psycopg.connect")
def test_janitor_exit_drops_database(connect_mock: MagicMock) -> None:
    """Test __exit__ drops the database."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    connect_mock.return_value = mock_conn

    janitor = DatabaseJanitor(
        user="user",
        host="host",
        port="1234",
        dbname="testdb",
        version=10,
    )

    janitor.__enter__()
    initial_call_count = mock_cursor.execute.call_count
    janitor.__exit__(None, None, None)

    # drop() should have been called
    assert mock_cursor.execute.call_count > initial_call_count


def test_janitor_init_all_parameters() -> None:
    """Test DatabaseJanitor initialization with all parameters."""
    import psycopg

    janitor = DatabaseJanitor(
        user="testuser",
        host="testhost",
        port=5432,
        dbname="testdb",
        template_dbname="template_test",
        as_template=True,
        version="14.5",
        password="testpass",
        isolation_level=psycopg.IsolationLevel.READ_COMMITTED,
        connection_timeout=120,
    )

    assert janitor.user == "testuser"
    assert janitor.host == "testhost"
    assert janitor.port == 5432
    assert janitor.dbname == "testdb"
    assert janitor.template_dbname == "template_test"
    assert janitor.as_template is True
    assert janitor.password == "testpass"
    assert janitor.version == parse("14.5")
    assert janitor.isolation_level == psycopg.IsolationLevel.READ_COMMITTED
    assert janitor._connection_timeout == 120
