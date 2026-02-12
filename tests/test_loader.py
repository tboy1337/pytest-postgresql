"""Tests for the `build_loader` function."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pytest_postgresql.loader import build_loader, sql
from tests.loader import load_database


def test_loader_callables() -> None:
    """Test handling callables in build_loader."""
    assert load_database == build_loader(load_database)
    assert load_database == build_loader("tests.loader:load_database")


def test_loader_sql() -> None:
    """Test returning partial running sql for the sql file path."""
    sql_path = Path("test_sql/eidastats.sql")
    loader_func = build_loader(sql_path)
    assert loader_func.args == (sql_path,)  # type: ignore
    assert loader_func.func == sql  # type: ignore


def test_build_loader_with_callable() -> None:
    """Test build_loader with a callable function."""

    def custom_loader(**kwargs: Any) -> None:
        pass

    result = build_loader(custom_loader)
    assert result is custom_loader


def test_build_loader_with_string_colon_separator() -> None:
    """Test build_loader with string using colon separator."""
    result = build_loader("tests.loader:load_database")
    assert result == load_database


def test_build_loader_with_string_dot_separator() -> None:
    """Test build_loader with string using dot separator."""
    result = build_loader("tests.loader.load_database")
    assert result == load_database


def test_build_loader_with_path() -> None:
    """Test build_loader with Path object."""
    sql_path = Path("test_sql/test.sql")
    result = build_loader(sql_path)

    assert callable(result)
    assert hasattr(result, "func")
    assert hasattr(result, "args")


def test_build_loader_with_different_paths() -> None:
    """Test build_loader with various Path objects."""
    paths = [
        Path("test.sql"),
        Path("subdir/test.sql"),
        Path("/absolute/path/test.sql"),
    ]

    for path in paths:
        result = build_loader(path)
        assert callable(result)


@patch("pytest_postgresql.loader.psycopg.connect")
@patch("builtins.open", new_callable=mock_open, read_data="SELECT 1;")
def test_sql_function(mock_file: Any, mock_connect: Any) -> None:
    """Test sql function loads SQL file."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value.__enter__.return_value = mock_conn

    sql_path = Path("test.sql")
    sql(
        sql_path,
        host="localhost",
        port=5432,
        user="user",
        dbname="testdb",
    )

    mock_file.assert_called_once_with(sql_path, "r")
    mock_cursor.execute.assert_called_once_with("SELECT 1;")
    mock_conn.commit.assert_called_once()


@patch("pytest_postgresql.loader.psycopg.connect")
@patch("builtins.open", new_callable=mock_open, read_data="CREATE TABLE test (id INT);")
def test_sql_function_with_create_statement(mock_file: Any, mock_connect: Any) -> None:
    """Test sql function with CREATE TABLE statement."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value.__enter__.return_value = mock_conn

    sql_path = Path("schema.sql")
    sql(sql_path, host="localhost", port=5432, user="user", dbname="testdb")

    mock_cursor.execute.assert_called_once_with("CREATE TABLE test (id INT);")


@patch("pytest_postgresql.loader.psycopg.connect")
@patch("builtins.open", new_callable=mock_open, read_data="")
def test_sql_function_with_empty_file(mock_file: Any, mock_connect: Any) -> None:
    """Test sql function with empty SQL file."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value.__enter__.return_value = mock_conn

    sql_path = Path("empty.sql")
    sql(sql_path, host="localhost", port=5432, user="user", dbname="testdb")

    mock_cursor.execute.assert_called_once_with("")
    mock_conn.commit.assert_called_once()


@patch("pytest_postgresql.loader.psycopg.connect")
def test_sql_function_with_password(mock_connect: Any) -> None:
    """Test sql function passes password to connection."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value.__enter__.return_value = mock_conn

    sql_path = Path("test.sql")
    with patch("builtins.open", mock_open(read_data="SELECT 1;")):
        sql(
            sql_path,
            host="localhost",
            port=5432,
            user="user",
            dbname="testdb",
            password="secret",
        )

    mock_connect.assert_called_once_with(
        host="localhost",
        port=5432,
        user="user",
        dbname="testdb",
        password="secret",
    )


def test_build_loader_invalid_string_format() -> None:
    """Test build_loader with invalid string format."""
    # Module doesn't exist
    with pytest.raises(ModuleNotFoundError):
        build_loader("nonexistent.module:function")


def test_build_loader_invalid_attribute() -> None:
    """Test build_loader with invalid attribute name."""
    # Module exists but attribute doesn't
    with pytest.raises(AttributeError):
        build_loader("tests.loader:nonexistent_function")
