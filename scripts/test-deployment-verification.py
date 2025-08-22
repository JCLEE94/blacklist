#!/usr/bin/env python3
"""
Test script for deployment verification system
Tests both local and live deployment verification
"""

import subprocess
import sys
import time
import json
import os
from pathlib import Path
import tempfile


class DeploymentVerificationTester:
    """Test the deployment verification system"""

    def __init__(self):
        self.script_path = Path("scripts/deployment-verification.py")
        self.test_results = []

    def run_test(
        self, test_name: str, command: list, expect_success: bool = True
    ) -> bool:
        """Run a test command and evaluate results"""
        print(f"\n🧪 Testing: {test_name}")
        print(f"🔨 Command: {' '.join(command)}")

        start_time = time.time()
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)

            duration = time.time() - start_time
            success = (result.returncode == 0) == expect_success

            test_result = {
                "test_name": test_name,
                "command": " ".join(command),
                "expected_success": expect_success,
                "actual_success": result.returncode == 0,
                "return_code": result.returncode,
                "duration": round(duration, 2),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "passed": success,
            }

            self.test_results.append(test_result)

            if success:
                print(f"✅ PASSED ({duration:.1f}s)")
                if result.stdout:
                    print(f"📤 Output: {result.stdout[:200]}...")
            else:
                print(f"❌ FAILED ({duration:.1f}s)")
                print(f"📤 Expected: {'success' if expect_success else 'failure'}")
                print(
                    f"📤 Actual: {'success' if result.returncode == 0 else 'failure'}"
                )
                if result.stderr:
                    print(f"🚨 Error: {result.stderr[:200]}...")

            return success

        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT (60s exceeded)")
            self.test_results.append(
                {
                    "test_name": test_name,
                    "command": " ".join(command),
                    "expected_success": expect_success,
                    "actual_success": False,
                    "return_code": -1,
                    "duration": 60.0,
                    "stdout": "",
                    "stderr": "Test timed out",
                    "passed": False,
                }
            )
            return False

        except Exception as e:
            print(f"💥 EXCEPTION: {e}")
            self.test_results.append(
                {
                    "test_name": test_name,
                    "command": " ".join(command),
                    "expected_success": expect_success,
                    "actual_success": False,
                    "return_code": -2,
                    "duration": time.time() - start_time,
                    "stdout": "",
                    "stderr": str(e),
                    "passed": False,
                }
            )
            return False

    def test_script_exists(self) -> bool:
        """Test that the deployment verification script exists"""
        if self.script_path.exists():
            print("✅ Deployment verification script exists")
            return True
        else:
            print("❌ Deployment verification script not found")
            return False

    def test_script_help(self) -> bool:
        """Test script help functionality"""
        return self.run_test(
            "Script Help", ["python3", str(self.script_path), "--help"]
        )

    def test_version_only_mode(self) -> bool:
        """Test version-only verification mode"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            success = self.run_test(
                "Version-only Mode",
                [
                    "python3",
                    str(self.script_path),
                    "--url",
                    "https://blacklist.jclee.me",
                    "--version-only",
                    "--json",
                    "--output",
                    output_file,
                ],
                expect_success=True,  # May fail if service is down, but test should work
            )

            # Check if output file was created
            if Path(output_file).exists():
                try:
                    with open(output_file, "r") as f:
                        data = json.load(f)
                    print(f"📊 Output file created with {len(data)} keys")
                    return True
                except json.JSONDecodeError:
                    print("⚠️ Output file exists but is not valid JSON")
                    return False
            else:
                print("⚠️ Output file was not created")
                return success

        finally:
            # Cleanup
            if Path(output_file).exists():
                os.unlink(output_file)

    def test_health_only_mode(self) -> bool:
        """Test health-only verification mode"""
        return self.run_test(
            "Health-only Mode",
            [
                "python3",
                str(self.script_path),
                "--url",
                "https://blacklist.jclee.me",
                "--health-only",
                "--timeout",
                "30",
            ],
        )

    def test_json_output(self) -> bool:
        """Test JSON output format"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            success = self.run_test(
                "JSON Output Format",
                [
                    "python3",
                    str(self.script_path),
                    "--url",
                    "https://blacklist.jclee.me",
                    "--json",
                    "--timeout",
                    "30",
                    "--output",
                    output_file,
                ],
            )

            # Validate JSON output
            if Path(output_file).exists():
                try:
                    with open(output_file, "r") as f:
                        data = json.load(f)
                    print(f"📊 Valid JSON output with keys: {list(data.keys())}")
                    return True
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON output: {e}")
                    return False

            return success

        finally:
            if Path(output_file).exists():
                os.unlink(output_file)

    def test_timeout_functionality(self) -> bool:
        """Test timeout functionality with short timeout"""
        return self.run_test(
            "Timeout Functionality",
            [
                "python3",
                str(self.script_path),
                "--url",
                "https://blacklist.jclee.me",
                "--timeout",
                "5",
            ],  # Very short timeout
            expect_success=False,  # Expect this to potentially timeout
        )

    def test_invalid_url(self) -> bool:
        """Test behavior with invalid URL"""
        return self.run_test(
            "Invalid URL Handling",
            [
                "python3",
                str(self.script_path),
                "--url",
                "https://nonexistent.invalid.domain.example.com",
                "--timeout",
                "10",
            ],
            expect_success=False,  # Should fail gracefully
        )

    def test_live_deployment_check(self) -> bool:
        """Test against live deployment (if available)"""
        return self.run_test(
            "Live Deployment Check",
            [
                "python3",
                str(self.script_path),
                "--url",
                "https://blacklist.jclee.me",
                "--timeout",
                "60",
            ],
        )

    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        passed_tests = sum(1 for test in self.test_results if test["passed"])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        report = f"""
# Deployment Verification Test Report

## 📊 Summary
- **Total Tests**: {total_tests}
- **Passed**: {passed_tests}
- **Failed**: {total_tests - passed_tests}
- **Success Rate**: {success_rate:.1f}%
- **Test Duration**: {sum(test['duration'] for test in self.test_results):.1f}s

## 🧪 Test Results

| Test Name | Status | Duration | Return Code |
|-----------|--------|----------|-------------|
"""

        for test in self.test_results:
            status = "✅ PASS" if test["passed"] else "❌ FAIL"
            report += f"| {test['test_name']} | {status} | {test['duration']}s | {test['return_code']} |\n"

        report += f"""
## 📋 Detailed Results

"""

        for test in self.test_results:
            report += f"""
### {test['test_name']}
- **Status**: {'✅ PASSED' if test['passed'] else '❌ FAILED'}
- **Command**: `{test['command']}`
- **Duration**: {test['duration']}s
- **Return Code**: {test['return_code']}
- **Expected**: {'Success' if test['expected_success'] else 'Failure'}
- **Actual**: {'Success' if test['actual_success'] else 'Failure'}

"""
            if test["stdout"]:
                report += f"**Output**:\n```\n{test['stdout'][:500]}\n```\n\n"

            if test["stderr"]:
                report += f"**Error**:\n```\n{test['stderr'][:500]}\n```\n\n"

        report += f"""
## 🎯 Conclusions

{'✅ All tests passed! Deployment verification system is working correctly.' if success_rate == 100 else f'⚠️ {total_tests - passed_tests} test(s) failed. Review the failures above.'}

## 📝 Recommendations

1. **Integration**: Add deployment verification to CI/CD pipeline
2. **Monitoring**: Set up automated verification on deployment
3. **Alerting**: Configure alerts for verification failures
4. **Documentation**: Update deployment procedures

---
*Generated by Deployment Verification Tester v1.0*
"""

        return report

    def run_all_tests(self) -> bool:
        """Run all verification tests"""
        print("🚀 Starting Deployment Verification System Tests")
        print("=" * 60)

        # Core functionality tests
        tests = [
            ("Script Exists", self.test_script_exists),
            ("Script Help", self.test_script_help),
            ("Version-only Mode", self.test_version_only_mode),
            ("Health-only Mode", self.test_health_only_mode),
            ("JSON Output", self.test_json_output),
            ("Invalid URL Handling", self.test_invalid_url),
            ("Live Deployment Check", self.test_live_deployment_check),
        ]

        all_passed = True

        for test_name, test_func in tests:
            try:
                if not test_func():
                    all_passed = False
            except Exception as e:
                print(f"💥 Test '{test_name}' threw exception: {e}")
                all_passed = False

        # Generate and save report
        report = self.generate_report()
        report_file = Path("deployment-verification-test-report.md")
        report_file.write_text(report)

        print(f"\n📄 Test report saved to: {report_file}")
        print(
            f"\n{'🎉 ALL TESTS PASSED!' if all_passed else '❌ Some tests failed - check report for details'}"
        )

        return all_passed


def main():
    """Main test function"""
    print("🔬 Deployment Verification System Tester")
    print("Testing deployment verification functionality...")

    tester = DeploymentVerificationTester()

    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
