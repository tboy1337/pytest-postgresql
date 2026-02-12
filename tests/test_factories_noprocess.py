"""Test noprocess factory module."""

from typing import Any
from unittest.mock import patch

import pytest

from pytest_postgresql.factories import noprocess


def test_xdistify_dbname_without_xdist() -> None:
    """Test xdistify_dbname without xdist."""
    with patch.dict("os.environ", {}, clear=True):
        result = noprocess.xdistify_dbname("testdb")
        assert result == "testdb"


def test_xdistify_dbname_with_xdist_gw0() -> None:
    """Test xdistify_dbname with xdist worker gw0."""
    with patch.dict("os.environ", {"PYTEST_XDIST_WORKER": "gw0"}):
        result = noprocess.xdistify_dbname("testdb")
        assert result == "testdbgw0"


def test_xdistify_dbname_with_xdist_gw1() -> None:
    """Test xdistify_dbname with xdist worker gw1."""
    with patch.dict("os.environ", {"PYTEST_XDIST_WORKER": "gw1"}):
        result = noprocess.xdistify_dbname("testdb")
        assert result == "testdbgw1"


def test_xdistify_dbname_with_various_dbnames() -> None:
    """Test xdistify_dbname with various database names."""
    test_cases = [
        ("mydb", "gw0", "mydbgw0"),
        ("test_db", "gw2", "test_dbgw2"),
        ("db123", "gw10", "db123gw10"),
        ("", "gw0", "gw0"),
    ]

    for dbname, worker, expected in test_cases:
        with patch.dict("os.environ", {"PYTEST_XDIST_WORKER": worker}):
            result = noprocess.xdistify_dbname(dbname)
            assert result == expected


def test_postgresql_noproc_returns_fixture() -> None:
    """Test postgresql_noproc returns a fixture function."""
    result = noprocess.postgresql_noproc()

    assert callable(result)
    # The function returned is wrapped by pytest.fixture decorator
    assert hasattr(result, "__wrapped__") or hasattr(result, "_pytestfixturefunction")


def test_postgresql_noproc_with_custom_parameters() -> None:
    """Test postgresql_noproc with custom parameters."""
    result = noprocess.postgresql_noproc(
        host="customhost",
        port="9999",
        user="customuser",
        password="custompass",
        dbname="customdb",
        options="-c work_mem=10MB",
    )

    assert callable(result)


def test_postgresql_noproc_with_load_parameter() -> None:
    """Test postgresql_noproc with load parameter."""

    def mock_loader(host: str, port: int, user: str, dbname: str, password: str) -> None:
        pass

    result = noprocess.postgresql_noproc(load=[mock_loader])

    assert callable(result)


def test_postgresql_noproc_with_depends_on() -> None:
    """Test postgresql_noproc with depends_on parameter."""
    result = noprocess.postgresql_noproc(depends_on="postgresql_proc")

    assert callable(result)


def test_postgresql_noproc_with_all_parameters() -> None:
    """Test postgresql_noproc with all parameters."""

    def mock_loader(host: str, port: int, user: str, dbname: str, password: str) -> None:
        pass

    result = noprocess.postgresql_noproc(
        host="localhost",
        port=5433,
        user="testuser",
        password="testpass",
        dbname="testdb",
        options="-c statement_timeout=30000",
        load=[mock_loader],
        depends_on="base_postgresql",
    )

    assert callable(result)


def test_postgresql_noproc_with_int_port() -> None:
    """Test postgresql_noproc with integer port."""
    result = noprocess.postgresql_noproc(port=5432)
    assert callable(result)


def test_postgresql_noproc_with_string_port() -> None:
    """Test postgresql_noproc with string port."""
    result = noprocess.postgresql_noproc(port="5433")
    assert callable(result)
