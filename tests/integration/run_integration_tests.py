#!/usr/bin/env python3
"""
Integration test runner for blacklist management system

This script runs all integration tests including inline tests.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def run_inline_tests():
    """Run inline integration tests in unified_routes.py"""
    print("\n" + "=" * 60)
    print("Running Inline Integration Tests")
    print("=" * 60)

    try:
        # Run the unified_routes module directly to execute inline tests
        result = subprocess.run(
            [sys.executable, "-m", "src.core.unified_routes"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to run inline tests: {e}")
        return False


def run_pytest_integration_tests():
    """Run pytest integration tests"""
    print("\n" + "=" * 60)
    print("Running PyTest Integration Tests")
    print("=" * 60)

    test_files = [
        "tests/integration/test_collection_endpoints_integration.py",
        "tests/integration/test_service_integration.py",
        "tests/integration/test_error_handling_edge_cases.py",
    ]

    all_passed = True

    for test_file in test_files:
        print(f"\n📋 Running {test_file}...")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
                cwd=project_root,
                capture_output=True,
                text=True,
            )

            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            if result.returncode != 0:
                all_passed = False
                print(f"❌ {test_file} failed!")
            else:
                print(f"✅ {test_file} passed!")

        except Exception as e:
            print(f"❌ Failed to run {test_file}: {e}")
            all_passed = False

    return all_passed


def run_integration_test_summary():
    """Generate test summary report"""
    print("\n" + "=" * 60)
    print("Integration Test Summary")
    print("=" * 60)

    try:
        # Run pytest with coverage for integration tests
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/",
                "--cov=src",
                "--cov-report=term-missing",
                "--quiet",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        # Extract coverage information
        output_lines = result.stdout.split("\n")
        coverage_started = False

        for line in output_lines:
            if "TOTAL" in line or coverage_started:
                print(line)
                coverage_started = True

    except Exception as e:
        print(f"Could not generate coverage report: {e}")


def main():
    """Main test runner"""
    print("🧪 Blacklist Management System - Integration Test Suite")
    print(f"📁 Running from: {project_root}")
    print(f"🐍 Python: {sys.version}")

    start_time = time.time()

    # Check if required packages are installed
    try:
        import unittest.mock

        import flask
        import pytest
    except ImportError as e:
        print(f"\n❌ Missing required package: {e}")
        print("Please install test dependencies:")
        print("  pip install -r requirements-dev.txt")
        return 1

    # Run tests
    inline_passed = run_inline_tests()
    pytest_passed = run_pytest_integration_tests()

    # Generate summary
    run_integration_test_summary()

    # Final report
    duration = time.time() - start_time

    print("\n" + "=" * 60)
    print("Final Test Results")
    print("=" * 60)
    print(f"⏱️  Total duration: {duration:.2f} seconds")
    print(f"📊 Inline tests: {'✅ PASSED' if inline_passed else '❌ FAILED'}")
    print(f"📊 PyTest tests: {'✅ PASSED' if pytest_passed else '❌ FAILED'}")

    if inline_passed and pytest_passed:
        print("\n🎉 All integration tests passed!")
        return 0
    else:
        print("\n❌ Some integration tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
