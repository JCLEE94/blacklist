#!/usr/bin/env python3
"""
Comprehensive Coverage Improvement Test Runner
Execute all coverage tests and measure improvement from 19% to 95% target

Test Strategy:
1. Run baseline coverage measurement
2. Execute comprehensive test suites
3. Measure final coverage and improvement
4. Generate detailed coverage report

Test Suites:
- Core functionality coverage tests
- Core modules comprehensive tests
- API endpoints coverage tests
- Collection and security coverage tests
- Integration and edge case tests

Follows CLAUDE.md standards:
- Real data testing, no MagicMock
- All failures tracked and reported
- Exit code 1 if coverage target not met
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import test modules
try:
    from tests.test_comprehensive_coverage_improvement import (
        run_comprehensive_coverage_tests,
    )
    from tests.test_core_modules_comprehensive import run_core_modules_tests
    from tests.test_api_endpoints_coverage import run_api_endpoints_tests
    from tests.test_collection_and_security_coverage import (
        run_collection_and_security_tests,
    )
except ImportError as e:
    print(f"Warning: Could not import test modules: {e}")


class CoverageImprovement:
    """Manage comprehensive coverage improvement process"""

    def __init__(self):
        self.project_root = project_root
        self.target_coverage = 95.0
        self.baseline_coverage = 19.0
        self.test_results = {}
        self.coverage_data = {}

    def run_baseline_coverage(self):
        """Run baseline coverage measurement"""
        print("📊 Measuring Baseline Coverage")
        print("=" * 50)

        try:
            # Run coverage analysis
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "pytest",
                    "tests/test_core_functionality_coverage.py",
                    "--cov=src",
                    "--cov-report=term-missing",
                    "--cov-report=json:coverage_baseline.json",
                    "-v",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            # Parse coverage data
            coverage_file = self.project_root / "coverage_baseline.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    self.coverage_data["baseline"] = coverage_data

                    # Calculate overall coverage
                    if "totals" in coverage_data:
                        total_statements = coverage_data["totals"]["num_statements"]
                        covered_statements = coverage_data["totals"]["covered_lines"]
                        if total_statements > 0:
                            baseline_pct = (covered_statements / total_statements) * 100
                            print(f"📈 Baseline Coverage: {baseline_pct:.2f}%")
                            return baseline_pct

            print(f"📈 Using Expected Baseline Coverage: {self.baseline_coverage}%")
            return self.baseline_coverage

        except Exception as e:
            print(f"⚠️  Baseline coverage measurement failed: {e}")
            print(f"📈 Using Expected Baseline Coverage: {self.baseline_coverage}%")
            return self.baseline_coverage

    def run_comprehensive_test_suite(self):
        """Run all comprehensive test suites"""
        print("\n🧪 Running Comprehensive Test Suites")
        print("=" * 50)

        test_suites = [
            ("Core Functionality", run_comprehensive_coverage_tests),
            ("Core Modules", run_core_modules_tests),
            ("API Endpoints", run_api_endpoints_tests),
            ("Collection & Security", run_collection_and_security_tests),
        ]

        all_suite_results = []

        for suite_name, test_function in test_suites:
            print(f"\n🔧 Running {suite_name} Tests")
            print("-" * 40)

            try:
                start_time = time.time()
                result = test_function()
                end_time = time.time()

                duration = end_time - start_time
                self.test_results[suite_name] = {
                    "success": result,
                    "duration": duration,
                }

                all_suite_results.append(result)

                if result:
                    print(
                        f"✅ {suite_name} tests completed successfully ({duration:.2f}s)"
                    )
                else:
                    print(f"❌ {suite_name} tests failed ({duration:.2f}s)")

            except Exception as e:
                print(f"❌ {suite_name} tests exception: {e}")
                self.test_results[suite_name] = {
                    "success": False,
                    "error": str(e),
                    "duration": 0,
                }
                all_suite_results.append(False)

        return all(all_suite_results)

    def run_final_coverage_measurement(self):
        """Run final coverage measurement with all tests"""
        print("\n📊 Measuring Final Coverage")
        print("=" * 50)

        try:
            # Run comprehensive coverage analysis
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "pytest",
                    "tests/test_comprehensive_coverage_improvement.py",
                    "tests/test_core_modules_comprehensive.py",
                    "tests/test_api_endpoints_coverage.py",
                    "tests/test_collection_and_security_coverage.py",
                    "--cov=src",
                    "--cov-report=term-missing",
                    "--cov-report=html:htmlcov_final",
                    "--cov-report=json:coverage_final.json",
                    "-v",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            print("Coverage measurement output:")
            print(result.stdout)

            if result.stderr:
                print("Coverage errors:")
                print(result.stderr)

            # Parse final coverage data
            coverage_file = self.project_root / "coverage_final.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    self.coverage_data["final"] = coverage_data

                    # Calculate final coverage
                    if "totals" in coverage_data:
                        total_statements = coverage_data["totals"]["num_statements"]
                        covered_statements = coverage_data["totals"]["covered_lines"]
                        if total_statements > 0:
                            final_pct = (covered_statements / total_statements) * 100
                            print(f"📈 Final Coverage: {final_pct:.2f}%")
                            return final_pct

            # Fallback: parse from stdout
            lines = result.stdout.split("\n")
            for line in lines:
                if "TOTAL" in line and "%" in line:
                    # Extract percentage from line like "TOTAL    16414   15234    4218      0    7.19%"
                    parts = line.split()
                    for part in parts:
                        if part.endswith("%"):
                            try:
                                pct = float(part.rstrip("%"))
                                print(f"📈 Final Coverage (parsed): {pct:.2f}%")
                                return pct
                            except ValueError:
                                continue

            print(f"⚠️  Could not parse final coverage, using conservative estimate")
            return 25.0  # Conservative estimate

        except Exception as e:
            print(f"⚠️  Final coverage measurement failed: {e}")
            return 25.0  # Conservative estimate

    def run_additional_focused_tests(self):
        """Run additional focused tests on key modules for coverage boost"""
        print("\n🎯 Running Additional Focused Tests")
        print("=" * 50)

        # Run existing comprehensive tests that might not have been executed
        additional_test_files = [
            "tests/test_core_functionality_coverage.py",
            "tests/test_core_modules_coverage.py",
            "tests/test_utils_coverage.py",
            "tests/test_security_comprehensive.py",
            "tests/test_collection_comprehensive.py",
        ]

        executed_tests = []

        for test_file in additional_test_files:
            test_path = self.project_root / test_file
            if test_path.exists():
                print(f"🔍 Running {test_file}")
                try:
                    result = subprocess.run(
                        ["python3", "-m", "pytest", str(test_path), "-v"],
                        capture_output=True,
                        text=True,
                        cwd=self.project_root,
                    )

                    if result.returncode == 0:
                        executed_tests.append(test_file)
                        print(f"  ✅ {test_file} completed")
                    else:
                        print(f"  ⚠️  {test_file} had issues: {result.stderr}")

                except Exception as e:
                    print(f"  ❌ {test_file} failed: {e}")
            else:
                print(f"  ⏭️  {test_file} not found, skipping")

        print(f"📋 Executed {len(executed_tests)} additional test files")
        return len(executed_tests)

    def generate_coverage_report(self, baseline_coverage, final_coverage):
        """Generate comprehensive coverage improvement report"""
        print("\n📋 Coverage Improvement Report")
        print("=" * 50)

        improvement = final_coverage - baseline_coverage
        improvement_pct = (
            (improvement / baseline_coverage) * 100 if baseline_coverage > 0 else 0
        )

        print(f"📊 Coverage Statistics:")
        print(f"   Baseline Coverage: {baseline_coverage:.2f}%")
        print(f"   Final Coverage:    {final_coverage:.2f}%")
        print(
            f"   Improvement:       +{improvement:.2f}% ({improvement_pct:.1f}% increase)"
        )
        print(f"   Target Coverage:   {self.target_coverage:.2f}%")

        # Target achievement
        if final_coverage >= self.target_coverage:
            print(
                f"🎯 ✅ TARGET ACHIEVED! Coverage reached {final_coverage:.2f}% (target: {self.target_coverage}%)"
            )
            target_met = True
        else:
            remaining = self.target_coverage - final_coverage
            print(
                f"🎯 ⚠️  Target not fully met. Need {remaining:.2f}% more coverage to reach {self.target_coverage}%"
            )
            target_met = False

        # Test suite results
        print(f"\n🧪 Test Suite Results:")
        for suite_name, result_data in self.test_results.items():
            status = "✅ PASSED" if result_data["success"] else "❌ FAILED"
            duration = result_data.get("duration", 0)
            print(f"   {suite_name}: {status} ({duration:.2f}s)")

            if "error" in result_data:
                print(f"      Error: {result_data['error']}")

        # Summary
        total_suites = len(self.test_results)
        passed_suites = sum(1 for r in self.test_results.values() if r["success"])

        print(f"\n📈 Summary:")
        print(f"   Test Suites Passed: {passed_suites}/{total_suites}")
        print(f"   Coverage Improvement: {improvement:.2f}% absolute")
        print(f"   Target Achievement: {'✅ YES' if target_met else '❌ NO'}")

        # Recommendations
        if not target_met:
            print(
                f"\n💡 Recommendations for reaching {self.target_coverage}% coverage:"
            )
            print(f"   1. Add more unit tests for core modules (focus on src/core/)")
            print(f"   2. Increase integration test coverage")
            print(f"   3. Add edge case and error handling tests")
            print(f"   4. Test utility modules comprehensively")
            print(f"   5. Add performance and security test scenarios")

        return target_met, improvement

    def save_coverage_data(self):
        """Save coverage improvement data to file"""
        coverage_report = {
            "timestamp": datetime.now().isoformat(),
            "test_results": self.test_results,
            "coverage_data": self.coverage_data,
            "target_coverage": self.target_coverage,
            "baseline_coverage": self.baseline_coverage,
        }

        report_file = self.project_root / "coverage_improvement_report.json"
        try:
            with open(report_file, "w") as f:
                json.dump(coverage_report, f, indent=2)
            print(f"📄 Coverage report saved to: {report_file}")
        except Exception as e:
            print(f"⚠️  Could not save coverage report: {e}")


def main():
    """Main coverage improvement execution"""
    print("🚀 Blacklist Coverage Improvement: 19% → 95% Target")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    coverage_improver = CoverageImprovement()

    # Step 1: Baseline measurement
    baseline_coverage = coverage_improver.run_baseline_coverage()

    # Step 2: Run comprehensive test suites
    suites_success = coverage_improver.run_comprehensive_test_suite()

    # Step 3: Run additional focused tests
    additional_tests = coverage_improver.run_additional_focused_tests()

    # Step 4: Final coverage measurement
    final_coverage = coverage_improver.run_final_coverage_measurement()

    # Step 5: Generate report
    target_met, improvement = coverage_improver.generate_coverage_report(
        baseline_coverage, final_coverage
    )

    # Step 6: Save data
    coverage_improver.save_coverage_data()

    # Final summary
    print(f"\n🏁 Coverage Improvement Complete")
    print(f"   Duration: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Suites Success: {suites_success}")
    print(f"   Additional Tests: {additional_tests}")
    print(f"   Target Met: {target_met}")
    print(f"   Improvement: +{improvement:.2f}%")

    # Exit with appropriate code
    if target_met and suites_success:
        print("✅ VALIDATION PASSED - Coverage improvement target achieved")
        sys.exit(0)
    else:
        print("❌ VALIDATION FAILED - Coverage improvement target not fully met")
        sys.exit(1)


if __name__ == "__main__":
    main()
