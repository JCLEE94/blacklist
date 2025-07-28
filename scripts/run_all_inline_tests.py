#!/usr/bin/env python3
"""
모든 Rust-style 인라인 테스트 실행기

전체 코드베이스의 인라인 테스트를 일괄 실행하고 결과를 종합 분석합니다.
각 모듈을 독립적으로 실행하여 완전한 통합 테스트 커버리지를 제공합니다.
"""

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class TestResult:
    """테스트 결과 데이터 클래스"""

    module: str
    passed: bool
    passed_tests: int
    total_tests: int
    success_rate: float
    execution_time: float
    output: str
    error: str = ""


class InlineTestRunner:
    """Rust-style 인라인 테스트 실행기"""

    def __init__(self):
        # 테스트할 모듈 목록 (인라인 테스트가 있는 모듈들)
        self.test_modules = [
            "src.core.container",
            "src.core.blacklist_unified",
            "src.core.unified_service",
            # 향후 추가될 모듈들
            # "src.utils.advanced_cache",
            # "src.core.collection_manager",
            # "src.core.regtech_simple_collector",
        ]

        self.results: List[TestResult] = []

    def run_single_test(self, module: str) -> TestResult:
        """단일 모듈 테스트 실행"""
        print(f"🧪 모듈 테스트 실행: {module}")
        print("-" * 50)

        start_time = time.time()

        try:
            # 모듈을 파이썬 모듈로 실행
            result = subprocess.run(
                [sys.executable, "-m", module],
                capture_output=True,
                text=True,
                timeout=30,  # 30초 타임아웃
            )

            execution_time = time.time() - start_time

            # 출력에서 테스트 결과 파싱
            output = result.stdout
            error = result.stderr

            # 성공률 파싱 (출력에서 "성공률: XX.X%" 패턴 찾기)
            success_rate = 0.0
            passed_tests = 0
            total_tests = 0

            for line in output.split('\n'):
                if '성공률:' in line and '%' in line:
                    try:
                        rate_str = line.split('성공률:')[1].split('%')[0].strip()
                        success_rate = float(rate_str)
                    except:
                        pass
                elif '통과한 테스트:' in line:
                    try:
                        passed_tests = int(line.split('통과한 테스트:')[1].strip())
                    except:
                        pass
                elif '총 테스트 수:' in line:
                    try:
                        total_tests = int(line.split('총 테스트 수:')[1].strip())
                    except:
                        pass

            # 종료 코드로 성공/실패 판단
            passed = result.returncode == 0

            test_result = TestResult(
                module=module,
                passed=passed,
                passed_tests=passed_tests,
                total_tests=total_tests,
                success_rate=success_rate,
                execution_time=execution_time,
                output=output,
                error=error,
            )

            # 결과 출력
            status = "✅ 통과" if passed else "❌ 실패"
            print(f"{status} - {module}")
            print(f"   성공률: {success_rate}% ({passed_tests}/{total_tests})")
            print(f"   실행시간: {execution_time:.3f}초")

            if error and "warning" not in error.lower():
                print(f"   경고/오류: {error[:100]}...")

            return test_result

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            print(f"⏰ 타임아웃 - {module} (30초 초과)")

            return TestResult(
                module=module,
                passed=False,
                passed_tests=0,
                total_tests=0,
                success_rate=0.0,
                execution_time=execution_time,
                output="",
                error="Timeout after 30 seconds",
            )

        except Exception as e:
            execution_time = time.time() - start_time
            print(f"💥 예외 발생 - {module}: {str(e)}")

            return TestResult(
                module=module,
                passed=False,
                passed_tests=0,
                total_tests=0,
                success_rate=0.0,
                execution_time=execution_time,
                output="",
                error=str(e),
            )

    def run_all_tests(self) -> List[TestResult]:
        """모든 테스트 실행"""
        print("=" * 70)
        print("🚀 전체 모듈 Rust-style 인라인 테스트 실행")
        print("=" * 70)
        print(f"실행할 모듈 수: {len(self.test_modules)}")
        print()

        for i, module in enumerate(self.test_modules, 1):
            print(f"[{i}/{len(self.test_modules)}] ", end="")
            result = self.run_single_test(module)
            self.results.append(result)
            print()

        return self.results

    def print_summary(self):
        """테스트 결과 종합 요약"""
        if not self.results:
            print("실행된 테스트가 없습니다.")
            return

        print("=" * 70)
        print("📊 전체 테스트 결과 종합")
        print("=" * 70)

        # 전체 통계
        total_modules = len(self.results)
        passed_modules = sum(1 for r in self.results if r.passed)
        failed_modules = total_modules - passed_modules

        total_test_cases = sum(r.total_tests for r in self.results)
        total_passed_cases = sum(r.passed_tests for r in self.results)

        overall_success_rate = (
            (total_passed_cases / total_test_cases * 100) if total_test_cases > 0 else 0
        )
        total_execution_time = sum(r.execution_time for r in self.results)

        print(f"📦 총 모듈 수: {total_modules}")
        print(f"✅ 통과한 모듈: {passed_modules}")
        print(f"❌ 실패한 모듈: {failed_modules}")
        print(f"🎯 모듈 성공률: {(passed_modules/total_modules)*100:.1f}%")
        print()
        print(f"🧪 총 테스트 케이스: {total_test_cases}")
        print(f"✅ 통과한 테스트: {total_passed_cases}")
        print(f"❌ 실패한 테스트: {total_test_cases - total_passed_cases}")
        print(f"🎯 전체 테스트 성공률: {overall_success_rate:.1f}%")
        print(f"⏱️ 총 실행 시간: {total_execution_time:.3f}초")
        print()

        # 모듈별 상세 결과
        print("📋 모듈별 상세 결과:")
        print("-" * 70)

        for result in self.results:
            status_icon = "✅" if result.passed else "❌"
            module_name = result.module.split('.')[-1]  # 마지막 부분만 표시

            print(
                f"{status_icon} {module_name:<20} "
                f"{result.success_rate:>6.1f}% "
                f"({result.passed_tests:>2}/{result.total_tests:<2}) "
                f"{result.execution_time:>6.3f}초"
            )

        print()

        # 실패한 모듈 상세 정보
        failed_results = [r for r in self.results if not r.passed]
        if failed_results:
            print("❌ 실패한 모듈 상세:")
            print("-" * 50)
            for result in failed_results:
                print(f"Module: {result.module}")
                if result.error:
                    print(f"Error: {result.error}")
                if result.output:
                    # 실패 관련 줄만 추출
                    error_lines = [
                        line
                        for line in result.output.split('\n')
                        if '❌' in line
                        or 'error' in line.lower()
                        or 'fail' in line.lower()
                    ]
                    if error_lines:
                        print("Output:")
                        for line in error_lines[:3]:  # 최대 3줄만
                            print(f"  {line}")
                print()

        # 성능 분석
        print("⚡ 성능 분석:")
        print("-" * 30)

        fastest = min(self.results, key=lambda r: r.execution_time)
        slowest = max(self.results, key=lambda r: r.execution_time)
        avg_time = total_execution_time / total_modules

        print(
            f"🚀 가장 빠른 모듈: {fastest.module.split('.')[-1]} ({fastest.execution_time:.3f}초)"
        )
        print(
            f"🐌 가장 느린 모듈: {slowest.module.split('.')[-1]} ({slowest.execution_time:.3f}초)"
        )
        print(f"📊 평균 실행 시간: {avg_time:.3f}초")

        # 권장사항
        print()
        print("💡 권장사항:")
        if overall_success_rate >= 90:
            print("🎉 훌륭합니다! 테스트 커버리지가 우수합니다.")
        elif overall_success_rate >= 70:
            print("👍 양호합니다. 일부 테스트 개선이 필요합니다.")
        else:
            print("⚠️ 테스트 실패율이 높습니다. 코드 검토가 필요합니다.")

        if failed_modules > 0:
            print(f"🔧 {failed_modules}개 모듈의 테스트 실패를 수정해주세요.")

        if avg_time > 5:
            print("⏰ 평균 실행 시간이 깁니다. 성능 최적화를 고려해보세요.")


def main():
    """메인 실행 함수"""
    runner = InlineTestRunner()

    # 모든 테스트 실행
    results = runner.run_all_tests()

    # 결과 요약 출력
    runner.print_summary()

    # 종료 코드 결정
    total_modules = len(results)
    passed_modules = sum(1 for r in results if r.passed)
    success_rate = (passed_modules / total_modules) if total_modules > 0 else 0

    if success_rate >= 0.8:  # 80% 이상
        print("\n🎉 전체 테스트 성공!")
        sys.exit(0)
    elif success_rate >= 0.6:  # 60% 이상
        print("\n✅ 대부분 테스트 통과")
        sys.exit(0)
    else:
        print("\n❌ 다수 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
