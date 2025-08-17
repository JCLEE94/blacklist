#!/usr/bin/env python3
"""
Security Test Runner

Runs all security tests with appropriate configuration.
"""

import subprocess
import sys


def run_security_tests():
    """Run all security tests"""
    test_files = [
        "tests/security/test_security_manager.py",
        "tests/security/test_security_headers.py",
        "tests/security/test_security_decorators.py",
        "tests/security/test_security_utilities.py",
    ]

    for test_file in test_files:
        print(f"\nRunning {test_file}...")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"✅ {test_file} passed")
        else:
            print(f"❌ {test_file} failed:")
            print(result.stdout)
            print(result.stderr)

    # Run all together with coverage
    print("\nRunning all security tests with coverage...")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/security/",
            "--cov=src.utils.security",
            "--cov-report=term-missing",
            "-v",
        ]
    )

    return result.returncode == 0


if __name__ == "__main__":
    success = run_security_tests()
    sys.exit(0 if success else 1)
