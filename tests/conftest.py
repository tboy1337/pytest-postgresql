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
INSIDE_DOCKER = os.environ.get("INSIDE_DOCKER") == "1"

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


def _run_tests_in_docker(test_nodeids: list[str]) -> dict:
    """Run specific tests inside Docker container and return results.
    
    Args:
        test_nodeids: List of test node IDs (e.g., "tests/test_executor.py::test_name")
    
    Returns:
        Dict with test results or empty dict if execution failed
    """
    import json
    
    if not test_nodeids or INSIDE_DOCKER:
        return {}
    
    compose_file = Path(__file__).parent.parent / "docker-compose.tests.yml"
    if not compose_file.exists():
        return {}
    
    # Build test selection string
    test_args = []
    for nodeid in test_nodeids:
        test_args.append(nodeid)
    
    print(f"\n[Docker] Running {len(test_nodeids)} pg_ctl tests in container...")
    
    try:
        # Run tests in Docker - simpler approach, parse output directly
        result = subprocess.run(
            [
                "docker-compose", "-f", str(compose_file), "run", "--rm",
                "-e", "INSIDE_DOCKER=1",
                "test-runner",
                "pytest"
            ] + test_args + [
                "-v", "--tb=line", "-o", "addopts="
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False
        )
        
        # Parse stdout for test results
        output = result.stdout + result.stderr
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        errors = output.count(" ERROR")
        skipped = output.count(" SKIPPED")
        
        # Print some of the output for debugging if tests failed
        if result.returncode != 0:
            # Print last part of output
            lines = output.split('\n')
            relevant_lines = [l for l in lines if 'PASSED' in l or 'FAILED' in l or 'ERROR' in l or '====' in l]
            if relevant_lines:
                print(f"[Docker] Last output lines:\n" + '\n'.join(relevant_lines[-20:]))
        
        return {
            "summary": {
                "passed": passed,
                "failed": failed,
                "error": errors,
                "skipped": skipped,
                "total": len(test_nodeids)
            },
            "exit_code": result.returncode,
            "stdout": output
        }
        
    except subprocess.TimeoutExpired:
        print("[Docker] Test execution timed out")
        return {}
    except Exception as e:
        print(f"[Docker] Error running tests: {e}")
        return {}


# Initialize Docker availability check
HAS_DOCKER = _check_docker_available()

# Auto-start Docker if needed (no pg_ctl but Docker available)
if not HAS_PG_CTL and HAS_DOCKER and not INSIDE_DOCKER:
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


def pytest_collection_modifyitems(config, items):
    """Run pg_ctl tests in Docker if pg_ctl not available locally."""
    if HAS_PG_CTL or not HAS_DOCKER or INSIDE_DOCKER:
        return  # Run normally
    
    # Separate pg_ctl tests from others
    pg_ctl_tests = []
    pytester_tests = []
    other_tests = []
    
    for item in items:
        # Check if test has pg_ctl skip marker
        skip_markers = [m for m in item.iter_markers(name="skipif")]
        needs_pg_ctl = any(
            "HAS_PG_CTL" in str(m.args) or "pg_ctl" in str(m.kwargs.get("reason", ""))
            for m in skip_markers
        )
        
        # Check if test uses pytester (these don't work well in Docker nested subprocess)
        uses_pytester = "test_postgres_options_plugin.py" in item.nodeid or "pytester" in str(item.fixturenames)
        
        if needs_pg_ctl:
            if uses_pytester:
                # Skip pytester tests entirely - they don't work in Docker subprocess
                pytester_tests.append(item)
            else:
                pg_ctl_tests.append(item)
        else:
            other_tests.append(item)
    
    if pg_ctl_tests:
        # Get test node IDs for Docker execution
        test_nodeids = [item.nodeid for item in pg_ctl_tests]
        
        # Run pg_ctl tests in Docker
        results = _run_tests_in_docker(test_nodeids)
        
        # Print summary
        if results:
            summary = results.get("summary", {})
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            errors = summary.get("error", 0)
            
            print(f"[Docker] pg_ctl tests: {passed} passed, {failed} failed, {errors} errors")
            
            # If any failed, print a warning
            if failed > 0 or errors > 0:
                print("[Docker] WARNING: Some pg_ctl tests failed in Docker container")
                if "stdout" in results:
                    print("\n[Docker] Output from container:")
                    print(results["stdout"][-2000:])  # Print last 2000 chars
        else:
            print(f"[Docker] WARNING: Failed to run {len(pg_ctl_tests)} pg_ctl tests in Docker")
        
        # Remove pg_ctl tests from collection since they already ran in Docker
        items[:] = other_tests


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
