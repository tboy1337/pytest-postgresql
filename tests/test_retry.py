"""Test retry module."""

import datetime
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pytest_postgresql.retry import get_current_datetime, retry


def test_retry_success_first_attempt() -> None:
    """Test retry succeeds on first attempt."""
    mock_func = MagicMock(return_value="success")

    result = retry(mock_func, timeout=10)

    assert result == "success"
    mock_func.assert_called_once()


def test_retry_success_after_failures() -> None:
    """Test retry succeeds after some failures."""
    mock_func = MagicMock(side_effect=[Exception("fail"), Exception("fail"), "success"])

    result = retry(mock_func, timeout=10, possible_exception=Exception)

    assert result == "success"
    assert mock_func.call_count == 3


def test_retry_timeout_exceeded() -> None:
    """Test retry raises TimeoutError when timeout is exceeded."""
    mock_func = MagicMock(side_effect=Exception("always fail"))

    with pytest.raises(TimeoutError) as exc_info:
        retry(mock_func, timeout=0, possible_exception=Exception)

    assert "Failed after" in str(exc_info.value)
    assert "attempts" in str(exc_info.value)


def test_retry_with_specific_exception() -> None:
    """Test retry only catches specified exception."""
    mock_func = MagicMock(side_effect=ValueError("specific error"))

    # Should catch ValueError
    with pytest.raises(TimeoutError):
        retry(mock_func, timeout=0, possible_exception=ValueError)

    # Should not catch other exceptions
    mock_func.side_effect = TypeError("different error")
    with pytest.raises(TypeError):
        retry(mock_func, timeout=10, possible_exception=ValueError)


def test_retry_default_exception() -> None:
    """Test retry with default Exception type."""
    mock_func = MagicMock(side_effect=[ValueError("fail"), "success"])

    result = retry(mock_func, timeout=10)

    assert result == "success"


def test_retry_default_timeout() -> None:
    """Test retry with default timeout."""
    mock_func = MagicMock(return_value="success")

    result = retry(mock_func)

    assert result == "success"


@patch("pytest_postgresql.retry.sleep")
@patch("pytest_postgresql.retry.get_current_datetime")
def test_retry_sleeps_between_attempts(
    mock_datetime: Any, mock_sleep: Any
) -> None:
    """Test retry sleeps between attempts."""
    # Simulate time progression
    start_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
    mock_datetime.side_effect = [
        start_time,  # Initial time
        start_time + datetime.timedelta(seconds=1),  # After first attempt
        start_time + datetime.timedelta(seconds=2),  # After second attempt
    ]

    mock_func = MagicMock(side_effect=[Exception("fail"), "success"])

    result = retry(mock_func, timeout=10, possible_exception=Exception)

    assert result == "success"
    mock_sleep.assert_called_with(1)


def test_retry_with_lambda() -> None:
    """Test retry with lambda function."""
    counter = {"value": 0}

    def increment() -> int:
        counter["value"] += 1
        if counter["value"] < 3:
            raise Exception("not ready")
        return counter["value"]

    result = retry(lambda: increment(), timeout=10, possible_exception=Exception)

    assert result == 3


def test_retry_preserves_return_type() -> None:
    """Test retry preserves the return type."""
    mock_int_func = MagicMock(return_value=42)
    result_int = retry(mock_int_func)
    assert result_int == 42

    mock_str_func = MagicMock(return_value="test")
    result_str = retry(mock_str_func)
    assert result_str == "test"

    mock_list_func = MagicMock(return_value=[1, 2, 3])
    result_list = retry(mock_list_func)
    assert result_list == [1, 2, 3]


def test_get_current_datetime_python_311_plus() -> None:
    """Test get_current_datetime for Python 3.11+."""
    if sys.version_info.major == 3 and sys.version_info.minor > 10:
        result = get_current_datetime()
        assert isinstance(result, datetime.datetime)
        # Should have timezone info for Python 3.11+
        assert result.tzinfo is not None
    else:
        pytest.skip("Test only for Python 3.11+")


def test_get_current_datetime_python_310_and_below() -> None:
    """Test get_current_datetime for Python 3.10 and below."""
    if sys.version_info.major == 3 and sys.version_info.minor <= 10:
        result = get_current_datetime()
        assert isinstance(result, datetime.datetime)
        # Should not have timezone info for Python 3.10 and below
        assert result.tzinfo is None
    else:
        pytest.skip("Test only for Python 3.10 and below")


def test_get_current_datetime_returns_datetime() -> None:
    """Test get_current_datetime returns a datetime object."""
    result = get_current_datetime()
    assert isinstance(result, datetime.datetime)


@patch("pytest_postgresql.retry.sys.version_info")
def test_get_current_datetime_mocked_python_311(mock_version_info: Any) -> None:
    """Test get_current_datetime with mocked Python 3.11."""
    mock_version_info.major = 3
    mock_version_info.minor = 11

    # Call the actual function - it will use datetime.UTC from datetime module
    result = get_current_datetime()

    # Just verify it returns a datetime object for Python 3.11+
    assert isinstance(result, datetime.datetime)


@patch("pytest_postgresql.retry.sys.version_info")
@patch("pytest_postgresql.retry.datetime.datetime")
def test_get_current_datetime_mocked_python_310(
    mock_datetime: Any, mock_version_info: Any
) -> None:
    """Test get_current_datetime with mocked Python 3.10."""
    mock_version_info.major = 3
    mock_version_info.minor = 10

    mock_dt = MagicMock()
    mock_datetime.utcnow.return_value = mock_dt

    result = get_current_datetime()

    assert result == mock_dt
    mock_datetime.utcnow.assert_called_once()


def test_retry_error_propagation() -> None:
    """Test that the original exception is preserved in TimeoutError."""
    original_error = ValueError("original error message")
    mock_func = MagicMock(side_effect=original_error)

    with pytest.raises(TimeoutError) as exc_info:
        retry(mock_func, timeout=0, possible_exception=ValueError)

    # Check that original exception is in the chain
    assert exc_info.value.__cause__ is original_error


def test_retry_multiple_exception_types() -> None:
    """Test retry with multiple exception attempts."""
    mock_func = MagicMock(
        side_effect=[
            ConnectionError("connection failed"),
            TimeoutError("timed out"),
            "success",
        ]
    )

    # Should catch Exception (base class)
    result = retry(mock_func, timeout=10, possible_exception=Exception)
    assert result == "success"
