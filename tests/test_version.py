"""Auxiliary tests."""

import pytest

import pytest_postgresql
from pytest_postgresql.executor import PostgreSQLExecutor


@pytest.mark.parametrize(
    "ctl_input, version",
    (
        ("pg_ctl (PostgreSQL) 10.18", "10.18"),
        ("pg_ctl (PostgreSQL) 11.13", "11.13"),
        ("pg_ctl (PostgreSQL) 12.8", "12.8"),
        ("pg_ctl (PostgreSQL) 13.4", "13.4"),
        ("pg_ctl (PostgreSQL) 14.0", "14.0"),
        ("pg_ctl (PostgreSQL) 16devel", "16"),
    ),
)
def test_versions(ctl_input: str, version: str) -> None:
    """Check correctness of the version regexp."""
    match = PostgreSQLExecutor.VERSION_RE.search(ctl_input)
    assert match is not None
    assert match.groupdict()["version"] == version


def test_package_version() -> None:
    """Test that package version is accessible."""
    assert hasattr(pytest_postgresql, "__version__")
    assert isinstance(pytest_postgresql.__version__, str)
    assert len(pytest_postgresql.__version__) > 0
    # Version should follow semantic versioning pattern (x.y.z)
    parts = pytest_postgresql.__version__.split(".")
    assert len(parts) >= 2  # At least major.minor
