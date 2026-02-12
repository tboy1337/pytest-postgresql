"""Test process factory module."""

import os
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from pytest_postgresql.config import PostgreSQLConfig
from pytest_postgresql.exceptions import ExecutableMissingException
from pytest_postgresql.factories import process


def test_pg_exe_with_explicit_executable() -> None:
    """Test _pg_exe with explicit executable provided."""
    config = PostgreSQLConfig(
        exec="pg_ctl_default",
        host="localhost",
        port="5432",
        port_search_count=5,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="tests",
        load=[],
        postgres_options="",
        drop_test_database=False,
    )
    result = process._pg_exe("custom_pg_ctl", config)
    assert result == "custom_pg_ctl"


@patch("pytest_postgresql.factories.process.os.path.exists")
def test_pg_exe_with_existing_config_executable(mock_exists: Any) -> None:
    """Test _pg_exe with config executable that exists."""
    mock_exists.return_value = True
    config = PostgreSQLConfig(
        exec="/usr/bin/pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=5,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="tests",
        load=[],
        postgres_options="",
        drop_test_database=False,
    )
    result = process._pg_exe(None, config)
    assert result == "/usr/bin/pg_ctl"


@patch("pytest_postgresql.factories.process.subprocess.check_output")
@patch("pytest_postgresql.factories.process.os.path.exists")
def test_pg_exe_finds_via_pg_config(mock_exists: Any, mock_check_output: Any) -> None:
    """Test _pg_exe finds executable via pg_config."""
    mock_exists.return_value = False
    mock_check_output.return_value = "/usr/local/pgsql/bin\n"
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=5,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="tests",
        load=[],
        postgres_options="",
        drop_test_database=False,
    )

    result = process._pg_exe(None, config)

    # Use os.path.join to get the correct path separator for the platform
    import os
    expected_path = os.path.join("/usr/local/pgsql/bin", "pg_ctl")
    assert result == expected_path
    mock_check_output.assert_called_once_with(
        ["pg_config", "--bindir"], universal_newlines=True
    )


@patch("pytest_postgresql.factories.process.subprocess.check_output")
@patch("pytest_postgresql.factories.process.os.path.exists")
def test_pg_exe_pg_config_not_found(mock_exists: Any, mock_check_output: Any) -> None:
    """Test _pg_exe when pg_config is not found."""
    mock_exists.return_value = False
    mock_check_output.side_effect = FileNotFoundError("pg_config not found")
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=5,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="tests",
        load=[],
        postgres_options="",
        drop_test_database=False,
    )

    with pytest.raises(ExecutableMissingException) as exc_info:
        process._pg_exe(None, config)

    assert "Could not find pg_config executable" in str(exc_info.value)


@patch("pytest_postgresql.factories.process.get_port")
def test_pg_port_with_explicit_port(mock_get_port: Any) -> None:
    """Test _pg_port with explicit port."""
    mock_get_port.return_value = 5433
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=5,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="tests",
        load=[],
        postgres_options="",
        drop_test_database=False,
    )

    result = process._pg_port(5433, config, [])

    assert result == 5433
    mock_get_port.assert_called_once_with(5433, [])


@patch("pytest_postgresql.factories.process.get_port")
def test_pg_port_with_config_port(mock_get_port: Any) -> None:
    """Test _pg_port falling back to config port."""
    mock_get_port.side_effect = [None, 5432]
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=5,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="tests",
        load=[],
        postgres_options="",
        drop_test_database=False,
    )

    result = process._pg_port(None, config, [5431])

    assert result == 5432
    assert mock_get_port.call_count == 2


@patch("pytest_postgresql.factories.process.get_port")
def test_pg_port_with_excluded_ports(mock_get_port: Any) -> None:
    """Test _pg_port respects excluded ports."""
    mock_get_port.return_value = 5434
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=5,
        user="postgres",
        password="",
        options="",
        startparams="",
        unixsocketdir="/tmp",
        dbname="tests",
        load=[],
        postgres_options="",
        drop_test_database=False,
    )
    excluded = [5432, 5433]

    result = process._pg_port(-1, config, excluded)

    assert result == 5434
    # Should be called with excluded ports
    mock_get_port.assert_called()


@patch("pytest_postgresql.factories.process.platform.system")
def test_prepare_dir_creates_structure(mock_system: Any, tmp_path: Path) -> None:
    """Test _prepare_dir creates datadir and logfile."""
    mock_system.return_value = "Linux"

    datadir, logfile = process._prepare_dir(tmp_path, 5432)

    assert datadir.exists()
    assert datadir.is_dir()
    assert datadir.name == "data-5432"
    assert logfile.name == "postgresql.5432.log"
    assert not logfile.exists()  # Should not create the log file, just path


@patch("pytest_postgresql.factories.process.platform.system")
def test_prepare_dir_freebsd_creates_pg_hba_conf(
    mock_system: Any, tmp_path: Path
) -> None:
    """Test _prepare_dir creates pg_hba.conf on FreeBSD."""
    mock_system.return_value = "FreeBSD"

    datadir, logfile = process._prepare_dir(tmp_path, 5432)

    pg_hba_path = datadir / "pg_hba.conf"
    assert pg_hba_path.exists()
    content = pg_hba_path.read_text()
    assert "host all all 0.0.0.0/0 trust" in content


def test_prepare_dir_with_different_ports(tmp_path: Path) -> None:
    """Test _prepare_dir with different port numbers."""
    datadir1, logfile1 = process._prepare_dir(tmp_path, 5432)
    datadir2, logfile2 = process._prepare_dir(tmp_path, 5433)

    assert datadir1.name == "data-5432"
    assert datadir2.name == "data-5433"
    assert logfile1.name == "postgresql.5432.log"
    assert logfile2.name == "postgresql.5433.log"


def test_postgresql_proc_returns_fixture() -> None:
    """Test postgresql_proc returns a fixture function."""
    result = process.postgresql_proc()

    assert callable(result)
    # The function returned is wrapped by pytest.fixture decorator
    assert hasattr(result, "__wrapped__") or hasattr(result, "_pytestfixturefunction")


def test_postgresql_proc_with_custom_parameters() -> None:
    """Test postgresql_proc with custom parameters."""
    result = process.postgresql_proc(
        executable="/custom/pg_ctl",
        host="customhost",
        port=9999,
        user="customuser",
        password="custompass",
        dbname="customdb",
        options="-c work_mem=10MB",
        startparams="-w",
        unixsocketdir="/custom/socket",
        postgres_options="-N 100",
    )

    assert callable(result)


def test_postgresql_proc_with_load_parameter() -> None:
    """Test postgresql_proc with load parameter."""

    def mock_loader(host: str, port: int, user: str, dbname: str, password: str) -> None:
        pass

    result = process.postgresql_proc(load=[mock_loader])

    assert callable(result)


def test_porttype_export() -> None:
    """Test that PortType is properly exported."""
    # PortType should be accessible from the module
    assert hasattr(process, "PortType")
    assert process.PortType is not None
