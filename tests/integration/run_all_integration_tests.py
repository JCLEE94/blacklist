#!/usr/bin/env python3
"""
마스터 통합 테스트 러너
모든 통합 테스트를 실행하고 종합 보고서 생성
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# 색상 코드
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def run_test_module(module_path):
    """개별 테스트 모듈 실행"""
    print(f"\n{Colors.BLUE}Running: {module_path}{Colors.RESET}")

    start_time = time.time()

    try:
        # Python 모듈로 실행
        result = subprocess.run(
            [sys.executable, module_path],
            capture_output=True,
            text=True,
            timeout=300,  # 5분 타임아웃
        )

        elapsed_time = time.time() - start_time

        # 결과 파싱
        output = result.stdout
        error = result.stderr

        # 성공/실패 카운트 추출
        passed = 0
        failed = 0

        for line in output.split("\n"):
            if "passed" in line and "failed" in line:
                # "X passed, Y failed" 패턴 찾기
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        try:
                            passed = int(parts[i - 1])
                        except:
                            pass
                    if part == "failed" and i > 0:
                        try:
                            failed = int(parts[i - 1])
                        except:
                            pass

        # 실패한 경우 stderr도 확인
        if result.returncode != 0 and failed == 0:
            failed = 1  # 최소 1개 실패로 표시

        return {
            "module": os.path.basename(module_path),
            "passed": passed,
            "failed": failed,
            "elapsed_time": elapsed_time,
            "returncode": result.returncode,
            "output": output,
            "error": error,
        }

    except subprocess.TimeoutExpired:
        return {
            "module": os.path.basename(module_path),
            "passed": 0,
            "failed": 1,
            "elapsed_time": 300,
            "returncode": -1,
            "output": "",
            "error": "Test timed out after 5 minutes",
        }
    except Exception as e:
        return {
            "module": os.path.basename(module_path),
            "passed": 0,
            "failed": 1,
            "elapsed_time": time.time() - start_time,
            "returncode": -1,
            "output": "",
            "error": str(e),
        }


def generate_report(results):
    """테스트 결과 보고서 생성"""
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_time = sum(r["elapsed_time"] for r in results)

    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}📊 INTEGRATION TEST SUMMARY REPORT{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")

    print(
        "\n{Colors.BOLD}Test Execution Time:{Colors.RESET} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(f"{Colors.BOLD}Total Duration:{Colors.RESET} {total_time:.2f} seconds")

    print(f"\n{Colors.BOLD}Overall Results:{Colors.RESET}")
    if total_failed == 0:
        print(f"  {Colors.GREEN}✅ ALL TESTS PASSED!{Colors.RESET}")
    else:
        print(f"  {Colors.RED}❌ SOME TESTS FAILED{Colors.RESET}")

    print(f"  Total Passed: {Colors.GREEN}{total_passed}{Colors.RESET}")
    print(f"  Total Failed: {Colors.RED}{total_failed}{Colors.RESET}")

    print(f"\n{Colors.BOLD}Detailed Results by Module:{Colors.RESET}")
    print(f"{'Module':<40} {'Status':<10} {'Passed':<8} {'Failed':<8} {'Time(s)':<10}")
    print("-" * 80)

    for result in results:
        module_name = (
            result["module"].replace("test_", "").replace("_integration.py", "")
        )
        status = (
            "{Colors.GREEN}PASS{Colors.RESET}"
            if result["failed"] == 0
            else "{Colors.RED}FAIL{Colors.RESET}"
        )

        print(
            "{module_name:<40} {status:<19} "
            "{result['passed']:<8} {result['failed']:<8} "
            "{result['elapsed_time']:<10.2f}"
        )

    # 실패한 테스트 상세 정보
    failed_tests = [r for r in results if r["failed"] > 0]
    if failed_tests:
        print(f"\n{Colors.BOLD}{Colors.RED}Failed Test Details:{Colors.RESET}")
        for result in failed_tests:
            print(f"\n{Colors.YELLOW}Module: {result['module']}{Colors.RESET}")
            if result["error"]:
                print(f"Error: {result['error']}")
            # 출력에서 실패 정보 추출
            output_lines = result["output"].split("\n")
            for line in output_lines:
                if "❌" in line or "failed" in line.lower() or "error" in line.lower():
                    print(f"  {line}")

    # 성능 통계
    print(f"\n{Colors.BOLD}Performance Statistics:{Colors.RESET}")
    avg_time = total_time / len(results) if results else 0
    print(f"  Average test duration: {avg_time:.2f}s")
    print(f"  Fastest test: {min(r['elapsed_time'] for r in results):.2f}s")
    print(f"  Slowest test: {max(r['elapsed_time'] for r in results):.2f}s")

    # JSON 보고서 저장
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_time": total_time,
        "results": results,
    }

    report_path = Path("tests/integration/test_report.json")
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n{Colors.BOLD}Report saved to:{Colors.RESET} {report_path}")

    return total_failed == 0


def main():
    """메인 실행 함수"""
    print(f"{Colors.BOLD}{Colors.PURPLE}")
    print("╔═══════════════════════════════════════════════════════╗")
    print("║     🚀 BLACKLIST INTEGRATION TEST SUITE 🚀           ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")

    # 테스트 모듈 찾기
    test_dir = Path(__file__).parent
    test_modules = sorted(
        [
            f
            for f in test_dir.glob("test_*.py")
            if f.name != "run_all_integration_tests.py"
        ]
    )

    if not test_modules:
        print(f"{Colors.RED}No test modules found!{Colors.RESET}")
        sys.exit(1)

    print(f"Found {len(test_modules)} test modules:")
    for module in test_modules:
        print(f"  • {module.name}")

    # 환경 준비
    print(f"\n{Colors.BOLD}Preparing test environment...{Colors.RESET}")
    os.environ["TESTING"] = "true"
    os.environ["FLASK_ENV"] = "testing"

    # 모든 테스트 실행
    results = []
    for i, module in enumerate(test_modules, 1):
        print(
            "\n{Colors.BOLD}[{i}/{len(test_modules)}] Testing {module.name}...{Colors.RESET}"
        )
        result = run_test_module(str(module))
        results.append(result)

        # 간단한 결과 표시
        if result["failed"] == 0:
            print(
                "{Colors.GREEN}✅ PASSED{Colors.RESET} ({result['passed']} tests in {result['elapsed_time']:.2f}s)"
            )
        else:
            print(
                "{Colors.RED}❌ FAILED{Colors.RESET} ({result['failed']} failures in {result['elapsed_time']:.2f}s)"
            )

    # 최종 보고서 생성
    success = generate_report(results)

    # 환경 정리
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
    if "FLASK_ENV" in os.environ:
        del os.environ["FLASK_ENV"]

    # 종료 코드
    if success:
        print(
            "\n{Colors.GREEN}{Colors.BOLD}🎉 All integration tests passed! 🎉{Colors.RESET}"
        )
        sys.exit(0)
    else:
        print(
            "\n{Colors.RED}{Colors.BOLD}💔 Some tests failed. Please check the details above.{Colors.RESET}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
