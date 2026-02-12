"""Tests to ensure module-level code is covered."""
# These imports at module level should trigger coverage of module-level code
import pytest_postgresql
import pytest_postgresql.config
import pytest_postgresql.exceptions
import pytest_postgresql.executor
import pytest_postgresql.executor_noop
import pytest_postgresql.factories
import pytest_postgresql.factories.client
import pytest_postgresql.factories.noprocess
import pytest_postgresql.factories.process
import pytest_postgresql.janitor
import pytest_postgresql.loader
import pytest_postgresql.plugin
import pytest_postgresql.retry


def test_module_level_imports_are_covered() -> None:
    """Verify that module-level imports triggered coverage."""
    # Verify key module attributes exist
    assert hasattr(pytest_postgresql, "__version__")
    assert hasattr(pytest_postgresql.config, "PostgreSQLConfig")
    assert hasattr(pytest_postgresql.exceptions, "ExecutableMissingException")
    assert hasattr(pytest_postgresql.exceptions, "PostgreSQLUnsupported")
    assert hasattr(pytest_postgresql.factories, "postgresql")
    assert hasattr(pytest_postgresql.factories, "postgresql_noproc")
    assert hasattr(pytest_postgresql.factories, "postgresql_proc")
    assert hasattr(pytest_postgresql.factories.client, "postgresql")
    assert hasattr(pytest_postgresql.factories.noprocess, "postgresql_noproc")
    assert hasattr(pytest_postgresql.factories.process, "postgresql_proc")
    assert hasattr(pytest_postgresql.janitor, "DatabaseJanitor")
    assert hasattr(pytest_postgresql.loader, "build_loader")
    assert hasattr(pytest_postgresql.loader, "sql")
    assert hasattr(pytest_postgresql.plugin, "pytest_addoption")
    assert hasattr(pytest_postgresql.retry, "retry")
    assert hasattr(pytest_postgresql.retry, "get_current_datetime")
    assert hasattr(pytest_postgresql.executor, "PostgreSQLExecutor")
    assert hasattr(pytest_postgresql.executor_noop, "NoopExecutor")


def test_exceptions_are_raisable() -> None:
    """Test that exceptions can be raised and caught."""
    from pytest_postgresql.exceptions import ExecutableMissingException, PostgreSQLUnsupported
    
    # Test ExecutableMissingException
    try:
        raise ExecutableMissingException("Test message")
    except ExecutableMissingException as e:
        assert str(e) == "Test message"
    
    # Test PostgreSQLUnsupported
    try:
        raise PostgreSQLUnsupported("Unsupported version")
    except PostgreSQLUnsupported as e:
        assert str(e) == "Unsupported version"


def test_config_dataclass_instantiation() -> None:
    """Test that PostgreSQLConfig can be instantiated."""
    from pytest_postgresql.config import PostgreSQLConfig
    from pathlib import Path
    
    config = PostgreSQLConfig(
        exec="pg_ctl",
        host="localhost",
        port="5432",
        port_search_count=5,
        user="postgres",
        password="secret",
        options="",
        startparams="-w",
        unixsocketdir="/tmp",
        dbname="test",
        load=[Path("/tmp/test.sql")],
        postgres_options="",
        drop_test_database=True,
    )
    
    assert config.exec == "pg_ctl"
    assert config.host == "localhost"
    assert config.port == "5432"
    assert config.user == "postgres"
