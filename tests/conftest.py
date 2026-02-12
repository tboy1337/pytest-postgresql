"""Tests main conftest file."""

import os
import shutil
import subprocess
from pathlib import Path

from pytest_postgresql import factories

pytest_plugins = ["pytester"]
POSTGRESQL_VERSION = os.environ.get("POSTGRES", "13")

# Auto-detect environment capabilities
HAS_PG_CTL = shutil.which("pg_ctl") is not None
HAS_DOCKER = False
DOCKER_AUTO_STARTED = False

# Export for use in skip markers
__all__ = ["HAS_PG_CTL", "HAS_DOCKER"]


def _check_docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            check=False,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _ensure_docker_postgres() -> bool:
    """Start Docker PostgreSQL if not running.
    
    Returns:
        True if Docker was started successfully, False otherwise.
    """
    global DOCKER_AUTO_STARTED
    
    compose_file = Path(__file__).parent.parent / "docker-compose.tests.yml"
    if not compose_file.exists():
        return False
    
    try:
        # Check if postgres-external is already running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=postgres-external", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10
        )
        
        if "postgres-external" in result.stdout:
            # Already running
            return True
        
        # Start Docker PostgreSQL
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "up", "-d", "postgres-external"],
            capture_output=True,
            check=False,
            timeout=60
        )
        
        if result.returncode == 0:
            DOCKER_AUTO_STARTED = True
            # Wait for PostgreSQL to be ready
            import time
            for _ in range(30):  # Wait up to 30 seconds
                health_check = subprocess.run(
                    ["docker", "exec", "pytest-postgresql-postgres-external-1",
                     "pg_isready", "-U", "postgres"],
                    capture_output=True,
                    check=False,
                    timeout=5
                )
                if health_check.returncode == 0:
                    return True
                time.sleep(1)
        
        return False
    except (subprocess.TimeoutExpired, Exception):
        return False


# Initialize Docker availability check
HAS_DOCKER = _check_docker_available()

# Auto-start Docker if needed (no pg_ctl but Docker available)
if not HAS_PG_CTL and HAS_DOCKER:
    if _ensure_docker_postgres():
        print("\n[Docker] Auto-started Docker PostgreSQL for testing")
    else:
        print("\n[Warning] Docker available but failed to start PostgreSQL container")
        HAS_DOCKER = False


TEST_SQL_DIR = os.path.dirname(os.path.abspath(__file__)) + "/test_sql/"
TEST_SQL_FILE = Path(TEST_SQL_DIR + "test.sql")
TEST_SQL_FILE2 = Path(TEST_SQL_DIR + "test2.sql")

# Docker-based fixtures for cross-platform compatibility
# Use environment variables or defaults for Docker PostgreSQL
DOCKER_HOST = os.environ.get("POSTGRESQL_HOST", "localhost")
DOCKER_PORT = int(os.environ.get("POSTGRESQL_PORT", "5433"))
DOCKER_USER = os.environ.get("POSTGRESQL_USER", "postgres")
DOCKER_PASSWORD = os.environ.get("POSTGRESQL_PASSWORD", "postgres")

# Configure fixtures based on available PostgreSQL
if HAS_PG_CTL:
    # Use native PostgreSQL with postgresql_proc
    postgresql_proc = factories.postgresql_proc()
    postgresql = factories.postgresql("postgresql_proc")
    
    # Additional fixtures using native PostgreSQL
    postgresql_proc2 = factories.postgresql_proc(
        load=[TEST_SQL_FILE, TEST_SQL_FILE2],
    )
    postgresql2 = factories.postgresql("postgresql_proc2", dbname="test-db")
    postgresql_load_1 = factories.postgresql("postgresql_proc2")
else:
    # Use Docker-based noproc fixtures (auto-started if needed)
    postgresql_noproc = factories.postgresql_noproc(
        host=DOCKER_HOST,
        port=DOCKER_PORT,
        user=DOCKER_USER,
        password=DOCKER_PASSWORD,
        dbname="tests_default",  # Unique dbname to avoid template conflicts
    )
    
    # Default postgresql client fixture
    postgresql = factories.postgresql("postgresql_noproc")
    
    # Use postgresql_noproc to connect to Docker container instead of postgresql_proc
    postgresql_proc2 = factories.postgresql_noproc(
        host=DOCKER_HOST,
        port=DOCKER_PORT,
        user=DOCKER_USER,
        password=DOCKER_PASSWORD,
        dbname="tests_proc2",  # Unique dbname to avoid template conflicts
        load=[TEST_SQL_FILE, TEST_SQL_FILE2],
    )
    postgresql2 = factories.postgresql("postgresql_proc2", dbname="test-db")
    postgresql_load_1 = factories.postgresql("postgresql_proc2")


def pytest_sessionfinish(session, exitstatus):
    """Clean up Docker if we auto-started it."""
    global DOCKER_AUTO_STARTED
    
    if DOCKER_AUTO_STARTED:
        compose_file = Path(__file__).parent.parent / "docker-compose.tests.yml"
        if compose_file.exists():
            print("\n[Docker] Cleaning up auto-started Docker PostgreSQL...")
            subprocess.run(
                ["docker-compose", "-f", str(compose_file), "down"],
                capture_output=True,
                check=False,
                timeout=30
            )
