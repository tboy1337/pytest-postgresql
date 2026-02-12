"""Test plugin module."""

from tempfile import gettempdir
from typing import Any
from unittest.mock import MagicMock

from pytest_postgresql import plugin


def test_plugin_help_messages_exist() -> None:
    """Test that all help messages are defined."""
    assert plugin._help_executable
    assert plugin._help_host
    assert plugin._help_port
    assert plugin._help_port_search_count
    assert plugin._help_user
    assert plugin._help_password
    assert plugin._help_options
    assert plugin._help_startparams
    assert plugin._help_unixsocketdir
    assert plugin._help_dbname
    assert plugin._help_load
    assert plugin._help_postgres_options
    assert plugin._help_drop_test_database


def test_pytest_addoption_registers_ini_options() -> None:
    """Test pytest_addoption registers ini options."""
    mock_parser = MagicMock()

    plugin.pytest_addoption(mock_parser)

    # Verify addini was called for each ini option
    ini_calls = [call for call in mock_parser.addini.call_args_list]
    ini_names = [call[1]["name"] for call in ini_calls]

    expected_ini_options = [
        "postgresql_exec",
        "postgresql_host",
        "postgresql_port",
        "postgresql_port_search_count",
        "postgresql_user",
        "postgresql_password",
        "postgresql_options",
        "postgresql_startparams",
        "postgresql_unixsocketdir",
        "postgresql_dbname",
        "postgresql_load",
        "postgresql_postgres_options",
    ]

    for option in expected_ini_options:
        assert option in ini_names


def test_pytest_addoption_registers_command_line_options() -> None:
    """Test pytest_addoption registers command line options."""
    mock_parser = MagicMock()

    plugin.pytest_addoption(mock_parser)

    # Verify addoption was called for each command line option
    option_calls = [call for call in mock_parser.addoption.call_args_list]
    option_names = [call[0][0] for call in option_calls]

    expected_options = [
        "--postgresql-exec",
        "--postgresql-host",
        "--postgresql-port",
        "--postgresql-port-search-count",
        "--postgresql-user",
        "--postgresql-password",
        "--postgresql-options",
        "--postgresql-startparams",
        "--postgresql-unixsocketdir",
        "--postgresql-dbname",
        "--postgresql-load",
        "--postgresql-postgres-options",
        "--postgresql-drop-test-database",
    ]

    for option in expected_options:
        assert option in option_names


def test_pytest_addoption_ini_defaults() -> None:
    """Test pytest_addoption sets correct ini defaults."""
    mock_parser = MagicMock()

    plugin.pytest_addoption(mock_parser)

    # Check specific defaults
    ini_calls = {call[1]["name"]: call[1] for call in mock_parser.addini.call_args_list}

    assert ini_calls["postgresql_exec"]["default"] == "/usr/lib/postgresql/13/bin/pg_ctl"
    assert ini_calls["postgresql_host"]["default"] == "127.0.0.1"
    assert ini_calls["postgresql_port"]["default"] is None
    assert ini_calls["postgresql_port_search_count"]["default"] == 5
    assert ini_calls["postgresql_user"]["default"] == "postgres"
    assert ini_calls["postgresql_password"]["default"] is None
    assert ini_calls["postgresql_options"]["default"] == ""
    assert ini_calls["postgresql_startparams"]["default"] == "-w"
    assert ini_calls["postgresql_unixsocketdir"]["default"] == gettempdir()
    assert ini_calls["postgresql_dbname"]["default"] == "tests"
    assert ini_calls["postgresql_postgres_options"]["default"] == ""


def test_pytest_addoption_load_type() -> None:
    """Test postgresql_load is configured as pathlist."""
    mock_parser = MagicMock()

    plugin.pytest_addoption(mock_parser)

    ini_calls = {call[1]["name"]: call[1] for call in mock_parser.addini.call_args_list}
    assert ini_calls["postgresql_load"]["type"] == "pathlist"


def test_pytest_addoption_command_line_actions() -> None:
    """Test command line options have correct actions."""
    mock_parser = MagicMock()

    plugin.pytest_addoption(mock_parser)

    option_calls = {call[0][0]: call[1] for call in mock_parser.addoption.call_args_list}

    # Most options should use "store" action
    assert option_calls["--postgresql-exec"]["action"] == "store"
    assert option_calls["--postgresql-host"]["action"] == "store"
    assert option_calls["--postgresql-port"]["action"] == "store"

    # postgresql_load should use "append"
    assert option_calls["--postgresql-load"]["action"] == "append"

    # drop_test_database should use "store_true"
    assert option_calls["--postgresql-drop-test-database"]["action"] == "store_true"


def test_pytest_addoption_command_line_destinations() -> None:
    """Test command line options have correct destinations."""
    mock_parser = MagicMock()

    plugin.pytest_addoption(mock_parser)

    option_calls = {call[0][0]: call[1] for call in mock_parser.addoption.call_args_list}

    expected_dests = {
        "--postgresql-exec": "postgresql_exec",
        "--postgresql-host": "postgresql_host",
        "--postgresql-port": "postgresql_port",
        "--postgresql-port-search-count": "postgresql_port_search_count",
        "--postgresql-user": "postgresql_user",
        "--postgresql-password": "postgresql_password",
        "--postgresql-options": "postgresql_options",
        "--postgresql-startparams": "postgresql_startparams",
        "--postgresql-unixsocketdir": "postgresql_unixsocketdir",
        "--postgresql-dbname": "postgresql_dbname",
        "--postgresql-load": "postgresql_load",
        "--postgresql-postgres-options": "postgresql_postgres_options",
        "--postgresql-drop-test-database": "postgresql_drop_test_database",
    }

    for option, expected_dest in expected_dests.items():
        assert option_calls[option]["dest"] == expected_dest


def test_plugin_default_fixtures_exist() -> None:
    """Test that default fixtures are created."""
    assert hasattr(plugin, "postgresql_proc")
    assert hasattr(plugin, "postgresql_noproc")
    assert hasattr(plugin, "postgresql")


def test_plugin_postgresql_proc_is_callable() -> None:
    """Test postgresql_proc fixture is callable."""
    assert callable(plugin.postgresql_proc)


def test_plugin_postgresql_noproc_is_callable() -> None:
    """Test postgresql_noproc fixture is callable."""
    assert callable(plugin.postgresql_noproc)


def test_plugin_postgresql_is_callable() -> None:
    """Test postgresql fixture is callable."""
    assert callable(plugin.postgresql)


def test_pytest_addoption_help_messages() -> None:
    """Test that help messages are passed to options."""
    mock_parser = MagicMock()

    plugin.pytest_addoption(mock_parser)

    # Check ini options have help
    ini_calls = {call[1]["name"]: call[1] for call in mock_parser.addini.call_args_list}
    for name, kwargs in ini_calls.items():
        assert "help" in kwargs
        assert len(kwargs["help"]) > 0

    # Check command line options have help
    option_calls = {call[0][0]: call[1] for call in mock_parser.addoption.call_args_list}
    for option, kwargs in option_calls.items():
        assert "help" in kwargs
        assert len(kwargs["help"]) > 0


def test_pytest_addoption_exec_has_metavar() -> None:
    """Test postgresql-exec option has metavar."""
    mock_parser = MagicMock()

    plugin.pytest_addoption(mock_parser)

    option_calls = {call[0][0]: call[1] for call in mock_parser.addoption.call_args_list}
    assert option_calls["--postgresql-exec"]["metavar"] == "path"
