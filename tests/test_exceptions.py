"""Test exception classes."""

from pytest_postgresql.exceptions import (
    ExecutableMissingException,
    PostgreSQLUnsupported,
)


def test_executable_missing_exception_instantiation() -> None:
    """Test ExecutableMissingException can be instantiated."""
    exc = ExecutableMissingException("pg_config not found")
    assert isinstance(exc, FileNotFoundError)
    assert str(exc) == "pg_config not found"


def test_executable_missing_exception_inheritance() -> None:
    """Test ExecutableMissingException inherits from FileNotFoundError."""
    exc = ExecutableMissingException("test")
    assert isinstance(exc, FileNotFoundError)
    assert isinstance(exc, Exception)


def test_executable_missing_exception_raise_catch() -> None:
    """Test ExecutableMissingException can be raised and caught."""
    try:
        raise ExecutableMissingException("Missing executable")
    except ExecutableMissingException as e:
        assert str(e) == "Missing executable"
    except Exception:
        assert False, "Should have caught ExecutableMissingException"


def test_postgresql_unsupported_instantiation() -> None:
    """Test PostgreSQLUnsupported can be instantiated."""
    exc = PostgreSQLUnsupported("PostgreSQL 8.x is not supported")
    assert isinstance(exc, Exception)
    assert str(exc) == "PostgreSQL 8.x is not supported"


def test_postgresql_unsupported_inheritance() -> None:
    """Test PostgreSQLUnsupported inherits from Exception."""
    exc = PostgreSQLUnsupported("test")
    assert isinstance(exc, Exception)
    assert not isinstance(exc, FileNotFoundError)


def test_postgresql_unsupported_raise_catch() -> None:
    """Test PostgreSQLUnsupported can be raised and caught."""
    try:
        raise PostgreSQLUnsupported("Unsupported version")
    except PostgreSQLUnsupported as e:
        assert str(e) == "Unsupported version"
    except Exception:
        assert False, "Should have caught PostgreSQLUnsupported"


def test_exception_with_empty_message() -> None:
    """Test exceptions with empty messages."""
    exc1 = ExecutableMissingException("")
    assert str(exc1) == ""

    exc2 = PostgreSQLUnsupported("")
    assert str(exc2) == ""


def test_exception_with_multiline_message() -> None:
    """Test exceptions with multiline messages."""
    msg = "Line 1\nLine 2\nLine 3"
    exc1 = ExecutableMissingException(msg)
    assert str(exc1) == msg

    exc2 = PostgreSQLUnsupported(msg)
    assert str(exc2) == msg
