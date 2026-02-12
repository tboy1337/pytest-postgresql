"""Test factories __init__ module."""

from pytest_postgresql import factories


def test_factories_all_exports() -> None:
    """Test that __all__ exports are correct."""
    assert hasattr(factories, "__all__")
    expected_exports = {"postgresql_proc", "postgresql_noproc", "postgresql", "PortType"}
    assert set(factories.__all__) == expected_exports


def test_postgresql_proc_import() -> None:
    """Test that postgresql_proc can be imported."""
    from pytest_postgresql.factories import postgresql_proc

    assert callable(postgresql_proc)


def test_postgresql_noproc_import() -> None:
    """Test that postgresql_noproc can be imported."""
    from pytest_postgresql.factories import postgresql_noproc

    assert callable(postgresql_noproc)


def test_postgresql_import() -> None:
    """Test that postgresql can be imported."""
    from pytest_postgresql.factories import postgresql

    assert callable(postgresql)


def test_porttype_import() -> None:
    """Test that PortType can be imported."""
    from pytest_postgresql.factories import PortType

    # PortType should be a type or union type
    assert PortType is not None


def test_all_exports_importable() -> None:
    """Test that all exports in __all__ are actually importable."""
    for name in factories.__all__:
        assert hasattr(factories, name), f"{name} is in __all__ but not importable"


def test_direct_module_access() -> None:
    """Test direct access to factory functions from the module."""
    assert hasattr(factories, "postgresql_proc")
    assert hasattr(factories, "postgresql_noproc")
    assert hasattr(factories, "postgresql")
    assert hasattr(factories, "PortType")
