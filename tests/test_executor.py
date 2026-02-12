"""Test various executor behaviours."""

import os
import platform
import subprocess
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import psycopg
import pytest
from packaging.version import parse

# Import environment detection from conftest
from tests.conftest import HAS_PG_CTL
from port_for import get_port
from psycopg import Connection
from pytest import FixtureRequest

import pytest_postgresql.factories.process as process
from pytest_postgresql.config import get_config
from pytest_postgresql.exceptions import (
    ExecutableMissingException,
    PostgreSQLUnsupported,
)
from pytest_postgresql.executor import PostgreSQLExecutor
from pytest_postgresql.factories import postgresql, postgresql_proc
from pytest_postgresql.retry import retry


def assert_executor_start_stop(executor: PostgreSQLExecutor) -> None:
    """Check that the executor is working."""
    with executor:
        assert executor.running()
        psycopg.connect(
            dbname=executor.user,
            user=executor.user,
            password=executor.password,
            host=executor.host,
            port=executor.port,
        )
        with pytest.raises(psycopg.OperationalError):
            psycopg.connect(
                dbname=executor.user,
                user=executor.user,
                password="bogus",
                host=executor.host,
                port=executor.port,
            )
    assert not executor.running()


class PatchedPostgreSQLExecutor(PostgreSQLExecutor):
    """PostgreSQLExecutor that always says it's 8.9 version."""

    @property
    def version(self) -> Any:
        """Overwrite version, to always return highest unsupported version."""
        return parse("8.9")


def test_unsupported_version(request: FixtureRequest) -> None:
    """Check that the error gets raised on unsupported postgres version."""
    config = get_config(request)
    port = get_port(config.port)
    assert port is not None
    executor = PatchedPostgreSQLExecutor(
        executable=config.exec,
        host=config.host,
        port=port,
        datadir="/tmp/error",
        unixsocketdir=config.unixsocketdir,
        logfile="/tmp/version.error.log",
        startparams=config.startparams,
        dbname="random_name",
    )

    with pytest.raises(PostgreSQLUnsupported):
        executor.start()


@pytest.mark.xdist_group(name="executor_no_xdist_guard")
@pytest.mark.parametrize("locale", ("en_US.UTF-8", "de_DE.UTF-8", "nl_NO.UTF-8"))
@pytest.mark.skipif(not HAS_PG_CTL, reason="Requires pg_ctl (auto-starts via Docker if available)")
def test_executor_init_with_password(
    request: FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
    locale: str,
) -> None:
    """Test whether the executor initializes properly."""
    config = get_config(request)
    monkeypatch.setenv("LC_ALL", locale)
    pg_exe = process._pg_exe(None, config)
    port = process._pg_port(-1, config, [])
    tmpdir = tmp_path_factory.mktemp(f"pytest-postgresql-{request.node.name}")
    datadir, logfile_path = process._prepare_dir(tmpdir, port)
    executor = PostgreSQLExecutor(
        executable=pg_exe,
        host=config.host,
        port=port,
        datadir=str(datadir),
        unixsocketdir=config.unixsocketdir,
        logfile=str(logfile_path),
        startparams=config.startparams,
        password="somepassword",
        dbname="somedatabase",
    )
    assert_executor_start_stop(executor)


@pytest.mark.skipif(not HAS_PG_CTL, reason="Requires pg_ctl (auto-starts via Docker if available)")
def test_executor_init_bad_tmp_path(
    request: FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    r"""Test init with \ and space chars in the path."""
    config = get_config(request)
    pg_exe = process._pg_exe(None, config)
    port = process._pg_port(-1, config, [])
    tmpdir = tmp_path_factory.mktemp(f"pytest-postgresql-{request.node.name}") / r"a bad\path/"
    tmpdir.mkdir(exist_ok=True)
    datadir, logfile_path = process._prepare_dir(tmpdir, port)
    executor = PostgreSQLExecutor(
        executable=pg_exe,
        host=config.host,
        port=port,
        datadir=str(datadir),
        unixsocketdir=config.unixsocketdir,
        logfile=str(logfile_path),
        startparams=config.startparams,
        password="some password",
        dbname="some database",
    )
    assert_executor_start_stop(executor)


postgres_with_password = postgresql_proc(password="hunter2")


@pytest.mark.skipif(not HAS_PG_CTL, reason="Requires pg_ctl (auto-starts via Docker if available)")
def test_proc_with_password(
    postgres_with_password: PostgreSQLExecutor,
) -> None:
    """Check that password option to postgresql_proc factory is honored."""
    assert postgres_with_password.running() is True

    # no assertion necessary here; we just want to make sure it connects with
    # the password
    retry(
        lambda: psycopg.connect(
            dbname=postgres_with_password.user,
            user=postgres_with_password.user,
            password=postgres_with_password.password,
            host=postgres_with_password.host,
            port=postgres_with_password.port,
        ),
        possible_exception=psycopg.OperationalError,
    )

    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(
            dbname=postgres_with_password.user,
            user=postgres_with_password.user,
            password="bogus",
            host=postgres_with_password.host,
            port=postgres_with_password.port,
        )


postgresql_max_conns_proc = postgresql_proc(postgres_options="-N 42")
postgres_max_conns = postgresql("postgresql_max_conns_proc")


@pytest.mark.skipif(not HAS_PG_CTL, reason="Requires pg_ctl (auto-starts via Docker if available)")
def test_postgres_options(postgres_max_conns: Connection) -> None:
    """Check that max connections (-N 42) is honored."""
    cur = postgres_max_conns.cursor()
    cur.execute("SHOW max_connections")
    assert cur.fetchone() == ("42",)


postgres_isolation_level = postgresql("postgresql_proc", isolation_level=psycopg.IsolationLevel.SERIALIZABLE)


@pytest.mark.skipif(not HAS_PG_CTL, reason="Requires pg_ctl (auto-starts via Docker if available)")
def test_custom_isolation_level(postgres_isolation_level: Connection) -> None:
    """Check that a client fixture with a custom isolation level works."""
    cur = postgres_isolation_level.cursor()
    cur.execute("SELECT 1")
    assert cur.fetchone() == (1,)


def test_executor_template_dbname() -> None:
    """Test template_dbname property."""
    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )
    assert executor.template_dbname == "testdb_tmpl"


@patch("pytest_postgresql.executor.subprocess.check_output")
def test_executor_version_success(mock_check_output: Any) -> None:
    """Test version property with successful detection."""
    mock_check_output.return_value = b"pg_ctl (PostgreSQL) 14.5\n"

    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    version = executor.version
    assert version == parse("14.5")
    mock_check_output.assert_called_once_with(["pg_ctl", "--version"])


@patch("pytest_postgresql.executor.subprocess.check_output")
def test_executor_version_executable_missing(mock_check_output: Any) -> None:
    """Test version property when executable is missing."""
    mock_check_output.side_effect = FileNotFoundError("pg_ctl not found")

    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    with pytest.raises(ExecutableMissingException) as exc_info:
        _ = executor.version

    assert "Could not found pg_ctl" in str(exc_info.value)


@patch("pytest_postgresql.executor.os.path.exists")
@patch("pytest_postgresql.executor.subprocess.getstatusoutput")
def test_executor_running_true(mock_getstatusoutput: Any, mock_exists: Any) -> None:
    """Test running() when server is running."""
    mock_exists.return_value = True
    mock_getstatusoutput.return_value = (0, "server is running")

    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    assert executor.running() is True
    mock_exists.assert_called_once_with("/tmp/data")


@patch("pytest_postgresql.executor.os.path.exists")
def test_executor_running_false_no_datadir(mock_exists: Any) -> None:
    """Test running() when datadir doesn't exist."""
    mock_exists.return_value = False

    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    assert executor.running() is False
    mock_exists.assert_called_once_with("/tmp/data")


@patch("pytest_postgresql.executor.os.path.exists")
@patch("pytest_postgresql.executor.subprocess.getstatusoutput")
def test_executor_running_false_not_running(
    mock_getstatusoutput: Any, mock_exists: Any
) -> None:
    """Test running() when server is not running."""
    mock_exists.return_value = True
    mock_getstatusoutput.return_value = (1, "no server running")

    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    assert executor.running() is False


@patch("pytest_postgresql.executor.os.path.isdir")
@patch("pytest_postgresql.executor.shutil.rmtree")
def test_executor_clean_directory_exists(
    mock_rmtree: Any, mock_isdir: Any
) -> None:
    """Test clean_directory when directory exists."""
    mock_isdir.return_value = True

    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    executor.clean_directory()

    mock_isdir.assert_called_once_with("/tmp/data")
    mock_rmtree.assert_called_once_with("/tmp/data")
    assert executor._directory_initialised is False


@patch("pytest_postgresql.executor.os.path.isdir")
@patch("pytest_postgresql.executor.shutil.rmtree")
def test_executor_clean_directory_not_exists(
    mock_rmtree: Any, mock_isdir: Any
) -> None:
    """Test clean_directory when directory doesn't exist."""
    mock_isdir.return_value = False

    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    executor.clean_directory()

    mock_isdir.assert_called_once_with("/tmp/data")
    mock_rmtree.assert_not_called()
    assert executor._directory_initialised is False


@patch("pytest_postgresql.executor.time.sleep")
def test_executor_wait_for_postgres_with_wait_flag(mock_sleep: Any) -> None:
    """Test wait_for_postgres with -w flag in startparams."""
    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="-w",
        dbname="testdb",
    )

    # Mock running() to return False then True
    with patch.object(executor, "running", side_effect=[False, False, True]):
        executor.wait_for_postgres()

    assert mock_sleep.call_count == 2


def test_executor_wait_for_postgres_without_wait_flag() -> None:
    """Test wait_for_postgres without -w flag in startparams."""
    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    # Should return immediately
    executor.wait_for_postgres()


@patch("pytest_postgresql.executor.subprocess.check_output")
def test_executor_init_directory_without_password(mock_check_output: Any) -> None:
    """Test init_directory without password."""
    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
        user="testuser",
    )

    with patch.object(executor, "clean_directory"):
        executor.init_directory()

    assert mock_check_output.called
    call_args = mock_check_output.call_args[0][0]
    assert "pg_ctl" in call_args
    assert "initdb" in call_args
    assert "--auth=trust" in " ".join(call_args)


@patch("pytest_postgresql.executor.subprocess.check_output")
@patch("pytest_postgresql.executor.tempfile.NamedTemporaryFile")
def test_executor_init_directory_with_password(
    mock_tempfile: Any, mock_check_output: Any
) -> None:
    """Test init_directory with password."""
    mock_file = MagicMock()
    mock_file.name = "/tmp/password_file"
    mock_tempfile.return_value.__enter__.return_value = mock_file

    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
        user="testuser",
        password="secret",
    )

    with patch.object(executor, "clean_directory"):
        executor.init_directory()

    mock_file.write.assert_called_once()
    mock_file.flush.assert_called_once()
    assert mock_check_output.called


def test_executor_init_directory_already_initialized() -> None:
    """Test init_directory when already initialized."""
    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    executor._directory_initialised = True

    with patch.object(executor, "clean_directory") as mock_clean:
        executor.init_directory()
        mock_clean.assert_not_called()


@patch("pytest_postgresql.executor.platform.system")
def test_executor_windows_terminate_process_no_process(mock_system: Any) -> None:
    """Test _windows_terminate_process when process is None."""
    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    executor.process = None
    executor._windows_terminate_process()  # Should not raise


@patch("pytest_postgresql.executor.platform.system")
def test_executor_windows_terminate_process_graceful(mock_system: Any) -> None:
    """Test _windows_terminate_process with graceful termination."""
    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    mock_process = MagicMock()
    executor.process = mock_process

    executor._windows_terminate_process()

    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called()


@patch("pytest_postgresql.executor.platform.system")
def test_executor_windows_terminate_process_force_kill(mock_system: Any) -> None:
    """Test _windows_terminate_process with force kill."""
    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    mock_process = MagicMock()
    mock_process.wait.side_effect = [subprocess.TimeoutExpired("cmd", 5), None]
    executor.process = mock_process

    executor._windows_terminate_process()

    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()


@patch("pytest_postgresql.executor.platform.system")
def test_executor_windows_terminate_process_exception(mock_system: Any) -> None:
    """Test _windows_terminate_process with exception."""
    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    mock_process = MagicMock()
    mock_process.terminate.side_effect = OSError("Process error")
    executor.process = mock_process

    # Should not raise
    executor._windows_terminate_process()


@patch("pytest_postgresql.executor.subprocess.check_output")
@patch("pytest_postgresql.executor.platform.system")
@patch.object(PostgreSQLExecutor, "_windows_terminate_process")
def test_executor_stop_windows(
    mock_windows_terminate: Any,
    mock_system: Any,
    mock_check_output: Any,
) -> None:
    """Test stop() on Windows."""
    mock_system.return_value = "Windows"

    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    result = executor.stop()

    assert result is executor
    mock_check_output.assert_called_once()
    mock_windows_terminate.assert_called_once()


@patch("pytest_postgresql.executor.subprocess.check_output")
def test_executor_del_cleanup(mock_check_output: Any) -> None:
    """Test __del__ cleanup."""
    executor = PostgreSQLExecutor(
        executable="pg_ctl",
        host="localhost",
        port=5432,
        datadir="/tmp/data",
        unixsocketdir="/tmp",
        logfile="/tmp/log.txt",
        startparams="",
        dbname="testdb",
    )

    with patch.object(executor, "clean_directory") as mock_clean:
        executor.__del__()
        mock_clean.assert_called_once()
