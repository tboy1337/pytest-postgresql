#!/usr/bin/env python3
"""Run pytest-postgresql tests in Docker container with PostgreSQL binaries.

This script builds and runs the Docker test environment that includes
PostgreSQL 17 binaries (pg_ctl, initdb, postgres) to run all tests
including those that require pg_ctl, regardless of the host OS.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

# Use colorama for cross-platform colored output
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        RED = ""
        GREEN = ""
        CYAN = ""
        YELLOW = ""
    
    class Style:
        RESET_ALL = ""
    
    COLORS_AVAILABLE = False


def print_colored(text: str, color: str = "") -> None:
    """Print colored text to stdout."""
    print(f"{color}{text}{Style.RESET_ALL}")


def print_header() -> None:
    """Print the script header."""
    print_colored("=" * 41, Fore.CYAN)
    print_colored("pytest-postgresql Docker Test Runner", Fore.CYAN)
    print_colored("=" * 41, Fore.CYAN)
    print()


def check_docker() -> bool:
    """Check if Docker is installed and running.
    
    Returns:
        True if Docker is available and running, False otherwise.
    """
    # Check if Docker is installed
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            print_colored("ERROR: Docker is not installed or not in PATH", Fore.RED)
            print_colored("Please install Docker Desktop from https://www.docker.com/products/docker-desktop", Fore.YELLOW)
            return False
        
        print_colored(f"Docker found: {result.stdout.strip()}", Fore.GREEN)
    except FileNotFoundError:
        print_colored("ERROR: Docker is not installed or not in PATH", Fore.RED)
        print_colored("Please install Docker Desktop from https://www.docker.com/products/docker-desktop", Fore.YELLOW)
        return False
    
    # Check if Docker daemon is running
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            print_colored("ERROR: Docker daemon is not running", Fore.RED)
            print_colored("Please start Docker Desktop", Fore.YELLOW)
            return False
        
        print_colored("Docker daemon is running", Fore.GREEN)
    except Exception as e:
        print_colored(f"ERROR: Failed to check Docker daemon: {e}", Fore.RED)
        return False
    
    print()
    return True


def build_image() -> int:
    """Build Docker test image.
    
    Returns:
        Exit code from docker-compose build command.
    """
    print_colored("Building Docker test image...", Fore.CYAN)
    
    result = subprocess.run(
        ["docker-compose", "-f", "docker-compose.tests.yml", "build", "test-runner"],
        check=False
    )
    
    if result.returncode != 0:
        print_colored("ERROR: Docker build failed", Fore.RED)
        return result.returncode
    
    print_colored("Docker image built successfully", Fore.GREEN)
    print()
    return 0


def run_tests(
    test_path: str,
    verbose: bool,
    coverage: bool,
    quiet: bool = False
) -> int:
    """Run tests in Docker container.
    
    Args:
        test_path: Path to test file or directory
        verbose: Whether to run pytest with verbose output
        coverage: Whether to generate coverage reports
        quiet: Whether to suppress informational messages
    
    Returns:
        Exit code from pytest command.
    """
    # Build pytest command
    pytest_cmd = f"pytest {test_path}"
    
    if verbose and not quiet:
        pytest_cmd += " -v"
    elif quiet:
        pytest_cmd += " -q"
    
    if coverage:
        pytest_cmd += " --cov=pytest_postgresql --cov-report=term --cov-report=html --cov-report=json --cov-branch"
    
    pytest_cmd += " --tb=short"
    
    if not quiet:
        print_colored("Running tests in Docker container...", Fore.CYAN)
        print(f"Command: {pytest_cmd}")
        print()
    
    # Run tests
    result = subprocess.run(
        ["docker-compose", "-f", "docker-compose.tests.yml", "run", "--rm", "test-runner", "bash", "-c", pytest_cmd],
        check=False
    )
    
    print()
    
    if result.returncode == 0:
        print_colored("=" * 41, Fore.GREEN)
        print_colored("All tests passed!", Fore.GREEN)
        print_colored("=" * 41, Fore.GREEN)
        
        if coverage:
            print()
            print_colored("Coverage reports generated:", Fore.CYAN)
            print("  - Terminal output (see above)")
            print("  - HTML: htmlcov/index.html")
            print("  - JSON: coverage.json")
            
            # Run check_coverage.py if it exists
            if Path("check_coverage.py").exists():
                print()
                print_colored("Running coverage analysis...", Fore.CYAN)
                subprocess.run([sys.executable, "check_coverage.py"], check=False)
    else:
        print_colored("=" * 41, Fore.RED)
        print_colored(f"Tests failed with exit code: {result.returncode}", Fore.RED)
        print_colored("=" * 41, Fore.RED)
    
    return result.returncode


def cleanup() -> None:
    """Clean up Docker containers."""
    print()
    print_colored("Cleaning up...", Fore.CYAN)
    subprocess.run(
        ["docker-compose", "-f", "docker-compose.tests.yml", "down"],
        capture_output=True,
        check=False
    )


def main() -> NoReturn:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Run pytest-postgresql tests in Docker container with PostgreSQL binaries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run all tests with coverage
  %(prog)s tests/test_executor.py       # Run specific test file
  %(prog)s --build-only                 # Only build the Docker image
  %(prog)s --no-build                   # Skip building, use existing image
  %(prog)s --no-coverage                # Run without coverage
  %(prog)s --quiet                      # Less verbose output
        """
    )
    
    parser.add_argument(
        "test_path",
        nargs="?",
        default="tests/",
        help="Specific test file or directory to run (default: tests/)"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        default=True,
        help="Generate coverage reports (default: enabled)"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_false",
        dest="coverage",
        help="Run without coverage reporting"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Run tests with verbose output (default: enabled)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Less verbose output"
    )
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Only build the Docker image without running tests"
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip building and use existing Docker image"
    )
    
    args = parser.parse_args()
    
    # Print header
    print_header()
    
    # Check Docker availability
    if not check_docker():
        sys.exit(1)
    
    # Build Docker image if needed
    if not args.no_build:
        exit_code = build_image()
        if exit_code != 0:
            sys.exit(exit_code)
    
    # If build-only, exit here
    if args.build_only:
        print_colored("Build complete. Use --no-build flag to skip building next time.", Fore.GREEN)
        sys.exit(0)
    
    # Run tests
    try:
        exit_code = run_tests(
            test_path=args.test_path,
            verbose=args.verbose,
            coverage=args.coverage,
            quiet=args.quiet
        )
    finally:
        # Always cleanup
        cleanup()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
