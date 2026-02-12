"""Config tests."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from _pytest._py.path import LocalPath

from pytest_postgresql.config import PostgreSQLConfig, detect_paths, get_config


@pytest.mark.parametrize(
    "path, want",
    (
        ("test.sql", Path("test.sql")),
        ("load.function", "load.function"),
        (LocalPath("test.sql"), Path("test.sql").absolute()),  # type: ignore[no-untyped-call]
    ),
)
def test_detect_paths(path: str | LocalPath, want: Path | str) -> None:
    """Check the correctness of detect_paths function."""
    assert detect_paths([path]) == [want]


def test_detect_paths_with_multiple_items() -> None:
    """Test detect_paths with multiple items."""
    paths = ["test1.sql", "load.function", "test2.sql"]
    result = detect_paths(paths)

    assert len(result) == 3
    assert result[0] == Path("test1.sql")
    assert result[1] == "load.function"
    assert result[2] == Path("test2.sql")


def test_detect_paths_with_empty_list() -> None:
    """Test detect_paths with empty list."""
    result = detect_paths([])
    assert result == []


def test_detect_paths_with_only_functions() -> None:
    """Test detect_paths with only function strings."""
    paths = ["module.function1", "package.module.function2"]
    result = detect_paths(paths)

    assert result == paths


def test_detect_paths_with_only_sql_files() -> None:
    """Test detect_paths with only SQL file paths."""
    paths = ["file1.sql", "dir/file2.sql", "../file3.sql"]
    result = detect_paths(paths)

    assert all(isinstance(p, Path) for p in result)
    assert len(result) == 3


def test_detect_paths_with_absolute_path() -> None:
    """Test detect_paths with absolute path."""
    paths = ["/absolute/path/test.sql"]
    result = detect_paths(paths)

    assert isinstance(result[0], Path)
    assert result[0] == Path("/absolute/path/test.sql")


def test_postgresql_config_dataclass() -> None:
    """Test PostgreSQLConfig dataclass creation."""
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=10,
        user="postgres",
        password="secret",
        options="-c log_statement=all",
        startparams="-w",
        unixsocketdir="/tmp",
        dbname="testdb",
        load=[],
        postgres_options="-N 100",
        drop_test_database=True,
    )

    assert config.exec == "pg_ctl"
    assert config.host == "localhost"
    assert config.port == "5432"
    assert config.port_search_count == 10
    assert config.user == "postgres"
    assert config.password == "secret"
    assert config.options == "-c log_statement=all"
    assert config.startparams == "-w"
    assert config.unixsocketdir == "/tmp"
    assert config.dbname == "testdb"
    assert config.load == []
    assert config.postgres_options == "-N 100"
    assert config.drop_test_database is True


def test_postgresql_config_frozen() -> None:
    """Test that PostgreSQLConfig is frozen."""
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=10,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="testdb",
        load=[],
        postgres_options="",
        drop_test_database=False,
    )

    # Should not be able to modify frozen dataclass
    with pytest.raises(AttributeError):
        config.host = "newhost"  # type: ignore[misc]


def test_get_config_reads_options() -> None:
    """Test get_config reads options from request."""
    mock_request = MagicMock()
    mock_config = MagicMock()
    mock_request.config = mock_config

    # Set up mock to return values
    def mock_getoption(name: str) -> Any:
        options = {
            "postgresql_exec": "custom_pg_ctl",
            "postgresql_host": "testhost",
            "postgresql_port": "9999",
            "postgresql_port_search_count": "20",
            "postgresql_user": "testuser",
            "postgresql_password": "testpass",
            "postgresql_options": "-c work_mem=10MB",
            "postgresql_startparams": "-w -t 30",
            "postgresql_unixsocketdir": "/custom/socket",
            "postgresql_dbname": "customdb",
            "postgresql_load": [],
            "postgresql_postgres_options": "-N 50",
            "postgresql_drop_test_database": True,
        }
        return options.get(name, "")

    def mock_getini(name: str) -> Any:
        return ""

    mock_config.getoption.side_effect = mock_getoption
    mock_config.getini.side_effect = mock_getini

    config = get_config(mock_request)

    assert config.exec == "custom_pg_ctl"
    assert config.host == "testhost"
    assert config.port == "9999"
    assert config.port_search_count == 20
    assert config.user == "testuser"
    assert config.password == "testpass"
    assert config.dbname == "customdb"


def test_get_config_falls_back_to_ini() -> None:
    """Test get_config falls back to ini values."""
    mock_request = MagicMock()
    mock_config = MagicMock()
    mock_request.config = mock_config

    def mock_getoption(name: str) -> Any:
        if name == "postgresql_drop_test_database":
            return False
        return None

    def mock_getini(name: str) -> Any:
        ini_options = {
            "postgresql_exec": "ini_pg_ctl",
            "postgresql_host": "ini_host",
            "postgresql_port": "5433",
            "postgresql_port_search_count": "5",
            "postgresql_user": "ini_user",
            "postgresql_password": "ini_pass",
            "postgresql_options": "",
            "postgresql_startparams": "",
            "postgresql_unixsocketdir": "/tmp",
            "postgresql_dbname": "ini_db",
            "postgresql_load": [],
            "postgresql_postgres_options": "",
        }
        return ini_options.get(name, "")

    mock_config.getoption.side_effect = mock_getoption
    mock_config.getini.side_effect = mock_getini

    config = get_config(mock_request)

    assert config.exec == "ini_pg_ctl"
    assert config.host == "ini_host"
    assert config.port == "5433"
    assert config.user == "ini_user"


def test_postgresql_config_with_none_port() -> None:
    """Test PostgreSQLConfig with None port."""
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port=None,
        port_search_count=10,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="testdb",
        load=[],
        postgres_options="",
        drop_test_database=False,
    )

    assert config.port is None


def test_postgresql_config_with_empty_load() -> None:
    """Test PostgreSQLConfig with empty load list."""
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=10,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="testdb",
        load=[],
        postgres_options="",
        drop_test_database=False,
    )

    assert config.load == []


def test_postgresql_config_with_load_paths() -> None:
    """Test PostgreSQLConfig with load paths."""
    load_paths = [Path("test1.sql"), "module.function", Path("test2.sql")]
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=10,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="testdb",
        load=load_paths,
        postgres_options="",
        drop_test_database=False,
    )

    assert len(config.load) == 3
    assert config.load[1] == "module.function"
