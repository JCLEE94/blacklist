#!/usr/bin/env python3
"""
Comprehensive Test Coverage Runner for Blacklist Management System

Runs all comprehensive test suites to achieve 95% enterprise test coverage.
Tests authentication, collection, analytics, and monitoring systems.

Usage:
    python3 tests/run_comprehensive_coverage_tests.py
    python3 tests/run_comprehensive_coverage_tests.py --live-system
    python3 tests/run_comprehensive_coverage_tests.py --coverage-only
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ComprehensiveTestRunner:
    """Manages execution of comprehensive test suites"""

    def __init__(self, live_system=False, coverage_only=False):
        self.live_system = live_system
        self.coverage_only = coverage_only
        self.base_url = (
            "https://blacklist.jclee.me" if live_system else "http://localhost:32542"
        )
        self.test_results = {}
        self.start_time = datetime.now()

    def run_test_file(self, test_file, description):
        """Run a single test file and capture results"""
        print(f"\n{'='*60}")
        print(f"🧪 Running {description}")
        print(f"📁 File: {test_file}")
        print(f"{'='*60}")

        start_time = time.time()

        try:
            # Set environment variable for live system testing
            env = os.environ.copy()
            if self.live_system:
                env["BLACKLIST_TEST_URL"] = self.base_url

            # Run the test file
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per test file
                env=env,
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                print(f"✅ {description} - PASSED ({duration:.1f}s)")
                self.test_results[test_file] = {
                    "status": "PASSED",
                    "duration": duration,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            else:
                print(f"❌ {description} - FAILED ({duration:.1f}s)")
                self.test_results[test_file] = {
                    "status": "FAILED",
                    "duration": duration,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }

                # Print error details
                if result.stderr:
                    print("Error output:")
                    print(result.stderr)
                if result.stdout:
                    print("Standard output:")
                    print(result.stdout)

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏱️ {description} - TIMEOUT ({duration:.1f}s)")
            self.test_results[test_file] = {
                "status": "TIMEOUT",
                "duration": duration,
                "error": "Test timed out after 5 minutes",
            }

        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {description} - ERROR ({duration:.1f}s)")
            self.test_results[test_file] = {
                "status": "ERROR",
                "duration": duration,
                "error": str(e),
            }

    def run_pytest_coverage(self):
        """Run pytest with coverage analysis"""
        print(f"\n{'='*60}")
        print("📊 Running Pytest with Coverage Analysis")
        print(f"{'='*60}")

        try:
            # Run pytest with coverage
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=json:coverage.json",
                "-v",
                "--tb=short",
                "tests/",
            ]

            if self.live_system:
                # Add markers for live system testing
                cmd.extend(["-m", "not slow"])

            print(f"Running: {' '.join(cmd)}")

            result = subprocess.run(cmd, timeout=600)  # 10 minute timeout

            if result.returncode == 0:
                print("✅ Pytest coverage analysis completed successfully")
                return True
            else:
                print(
                    f"❌ Pytest coverage analysis failed (exit code: {result.returncode})"
                )
                return False

        except subprocess.TimeoutExpired:
            print("⏱️ Pytest coverage analysis timed out")
            return False
        except Exception as e:
            print(f"💥 Pytest coverage analysis error: {e}")
            return False

    def run_comprehensive_tests(self):
        """Run all comprehensive test suites"""
        test_files = [
            ("tests/test_auth_comprehensive.py", "Authentication System Tests"),
            ("tests/test_collection_comprehensive.py", "Collection System Tests"),
            ("tests/test_analytics_comprehensive.py", "Analytics System Tests"),
            ("tests/test_monitoring_comprehensive.py", "Monitoring System Tests"),
        ]

        print(f"🚀 Starting Comprehensive Test Coverage Analysis")
        print(f"📅 Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Target System: {self.base_url}")
        print(f"📋 Test Files: {len(test_files)}")

        # Run each test file
        for test_file, description in test_files:
            test_path = project_root / test_file
            if test_path.exists():
                self.run_test_file(str(test_path), description)
            else:
                print(f"⚠️ Test file not found: {test_file}")
                self.test_results[test_file] = {
                    "status": "NOT_FOUND",
                    "error": "Test file does not exist",
                }

        # Run pytest coverage if requested
        if self.coverage_only or not self.live_system:
            coverage_success = self.run_pytest_coverage()
        else:
            coverage_success = None

        return coverage_success

    def generate_report(self):
        """Generate comprehensive test report"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE TEST COVERAGE REPORT")
        print(f"{'='*80}")

        print(f"🕐 Test Duration: {total_duration:.1f} seconds")
        print(f"📅 Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Target System: {self.base_url}")

        # Test results summary
        passed = sum(1 for r in self.test_results.values() if r["status"] == "PASSED")
        failed = sum(1 for r in self.test_results.values() if r["status"] == "FAILED")
        errors = sum(
            1
            for r in self.test_results.values()
            if r["status"] in ["ERROR", "TIMEOUT", "NOT_FOUND"]
        )
        total = len(self.test_results)

        print(f"\n📈 Test Suite Results:")
        print(f"  Total Test Suites: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Errors: {errors}")

        if total > 0:
            success_rate = (passed / total) * 100
            print(f"  Success Rate: {success_rate:.1f}%")

        # Detailed results
        print(f"\n📋 Detailed Results:")
        for test_file, result in self.test_results.items():
            status_icon = {
                "PASSED": "✅",
                "FAILED": "❌",
                "ERROR": "💥",
                "TIMEOUT": "⏱️",
                "NOT_FOUND": "⚠️",
            }.get(result["status"], "❓")

            duration = result.get("duration", 0)
            print(f"  {status_icon} {test_file} - {result['status']} ({duration:.1f}s)")

            if result["status"] in ["FAILED", "ERROR", "TIMEOUT"]:
                if "error" in result:
                    print(f"    Error: {result['error']}")
                if "stderr" in result and result["stderr"]:
                    print(f"    Stderr: {result['stderr'][:200]}...")

        # Coverage information
        coverage_file = project_root / "coverage.json"
        if coverage_file.exists():
            try:
                import json

                with open(coverage_file) as f:
                    coverage_data = json.load(f)

                total_coverage = coverage_data.get("totals", {}).get(
                    "percent_covered", 0
                )
                print(f"\n📊 Code Coverage: {total_coverage:.1f}%")

                if total_coverage >= 95:
                    print("🎯 EXCELLENT: Achieved 95%+ enterprise coverage target!")
                elif total_coverage >= 80:
                    print(
                        "🎯 GOOD: Achieved 80%+ coverage, approaching enterprise target"
                    )
                elif total_coverage >= 60:
                    print("🎯 FAIR: Achieved 60%+ coverage, needs improvement")
                else:
                    print("🎯 POOR: Coverage below 60%, significant improvement needed")

            except Exception as e:
                print(f"⚠️ Could not read coverage data: {e}")

        # Recommendations
        print(f"\n💡 Recommendations:")

        if failed > 0:
            print(f"  • Fix {failed} failing test suite(s)")

        if errors > 0:
            print(f"  • Resolve {errors} test execution error(s)")

        # Coverage-based recommendations
        coverage_file = project_root / "coverage.json"
        if coverage_file.exists():
            try:
                import json

                with open(coverage_file) as f:
                    coverage_data = json.load(f)

                files = coverage_data.get("files", {})
                low_coverage_files = [
                    filename
                    for filename, file_data in files.items()
                    if file_data.get("summary", {}).get("percent_covered", 100) < 80
                ]

                if low_coverage_files:
                    print(
                        f"  • Improve coverage for {len(low_coverage_files)} low-coverage files"
                    )
                    for filename in low_coverage_files[:5]:  # Show first 5
                        coverage_pct = (
                            files[filename].get("summary", {}).get("percent_covered", 0)
                        )
                        print(f"    - {filename}: {coverage_pct:.1f}%")

                    if len(low_coverage_files) > 5:
                        print(f"    ... and {len(low_coverage_files) - 5} more files")

            except Exception:
                pass

        # Success determination
        overall_success = (
            passed == total  # All test suites passed
            and total > 0  # At least some tests ran
        )

        if overall_success:
            print(f"\n🎉 COMPREHENSIVE TESTING SUCCESS!")
            print(f"   All {total} test suites passed successfully")
            print(f"   System is ready for enterprise production use")
        else:
            print(f"\n⚠️ COMPREHENSIVE TESTING INCOMPLETE")
            print(f"   {failed + errors} test suite(s) need attention")
            print(f"   Review failures and rerun tests")

        return overall_success


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run comprehensive test coverage analysis for Blacklist Management System"
    )
    parser.add_argument(
        "--live-system",
        action="store_true",
        help="Test against live system (blacklist.jclee.me) instead of localhost",
    )
    parser.add_argument(
        "--coverage-only",
        action="store_true",
        help="Only run pytest coverage analysis, skip comprehensive tests",
    )

    args = parser.parse_args()

    # Create test runner
    runner = ComprehensiveTestRunner(
        live_system=args.live_system, coverage_only=args.coverage_only
    )

    # Run tests
    coverage_success = runner.run_comprehensive_tests()

    # Generate report
    overall_success = runner.generate_report()

    # Exit with appropriate code
    if overall_success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
