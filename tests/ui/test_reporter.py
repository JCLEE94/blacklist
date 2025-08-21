"""
UI 테스트 리포터 모듈

테스트 결과 수집, 성능 메트릭 추적, 리포트 생성 기능을 제공합니다.
"""

import time
from typing import Dict, List, Optional


class UITestReporter:
    """테스트 결과 리포터"""

    def __init__(self):
        self.results = {
            "test_summary": {},
            "performance_metrics": {},
            "errors": [],
            "warnings": [],
            "passed_tests": [],
            "failed_tests": [],
        }

    def add_result(
        self,
        test_name: str,
        status: str,
        duration: float,
        details: Optional[Dict] = None,
    ):
        """테스트 결과 추가"""
        result = {
            "test_name": test_name,
            "status": status,
            "duration": duration,
            "details": details or {},
        }

        if status == "PASS":
            self.results["passed_tests"].append(result)
        elif status == "FAIL":
            self.results["failed_tests"].append(result)

    def add_performance_metric(self, metric_name: str, value: float, threshold: float):
        """성능 메트릭 추가"""
        self.results["performance_metrics"][metric_name] = {
            "value": value,
            "threshold": threshold,
            "status": "PASS" if value <= threshold else "FAIL",
        }

    def add_error(self, error_message: str, context: Optional[Dict] = None):
        """에러 추가"""
        self.results["errors"].append(
            {
                "message": error_message,
                "context": context or {},
                "timestamp": time.time(),
            }
        )

    def add_warning(self, warning_message: str, context: Optional[Dict] = None):
        """경고 추가"""
        self.results["warnings"].append(
            {
                "message": warning_message,
                "context": context or {},
                "timestamp": time.time(),
            }
        )

    def get_test_stats(self) -> Dict[str, int]:
        """테스트 통계 반환"""
        total_tests = len(self.results["passed_tests"]) + len(
            self.results["failed_tests"]
        )
        pass_rate = (
            (len(self.results["passed_tests"]) / total_tests * 100)
            if total_tests > 0
            else 0
        )

        return {
            "total": total_tests,
            "passed": len(self.results["passed_tests"]),
            "failed": len(self.results["failed_tests"]),
            "errors": len(self.results["errors"]),
            "warnings": len(self.results["warnings"]),
            "pass_rate": pass_rate,
        }

    def get_performance_summary(self) -> Dict[str, str]:
        """성능 메트릭 요약 반환"""
        summary = []

        for metric_name, data in self.results["performance_metrics"].items():
            status_icon = "✅" if data["status"] == "PASS" else "❌"
            summary.append(
                f"  {status_icon} {metric_name}: {data['value']:.2f}ms (임계값: {data['threshold']}ms)"
            )

        return summary

    def generate_report(self) -> str:
        """종합 리포트 생성"""
        stats = self.get_test_stats()
        performance_summary = self.get_performance_summary()

        report = [
            "=" * 80,
            "📊 blacklist.jclee.me 포괄적 UI 테스트 리포트",
            "=" * 80,
            f"총 테스트: {stats['total']}",
            f"성공: {stats['passed']}",
            f"실패: {stats['failed']}",
            f"성공률: {stats['pass_rate']:.1f}%",
            f"에러: {stats['errors']}",
            f"경고: {stats['warnings']}",
            "",
            "🚀 성능 메트릭:",
        ]

        report.extend(performance_summary)

        if self.results["failed_tests"]:
            report.extend(
                [
                    "",
                    "❌ 실패한 테스트:",
                ]
            )
            for test in self.results["failed_tests"]:
                report.append(
                    f"  - {test['test_name']}: {test.get('details', {}).get('error', 'Unknown error')}"
                )

        if self.results["errors"]:
            report.extend(
                [
                    "",
                    "🚨 발견된 에러:",
                ]
            )
            for error in self.results["errors"][:5]:  # 최대 5개만 표시
                report.append(f"  - {error['message']}")

        if self.results["warnings"]:
            report.extend(
                [
                    "",
                    "⚠️ 경고 사항:",
                ]
            )
            for warning in self.results["warnings"][:5]:  # 최대 5개만 표시
                report.append(f"  - {warning['message']}")

        report.append("=" * 80)
        return "\n".join(report)

    def has_failures(self) -> bool:
        """실패한 테스트가 있는지 확인"""
        return len(self.results["failed_tests"]) > 0

    def get_json_report(self) -> Dict:
        """리포트를 JSON 형식으로 반환"""
        return {
            "summary": self.get_test_stats(),
            "performance": self.results["performance_metrics"],
            "errors": self.results["errors"],
            "warnings": self.results["warnings"],
            "failed_tests": self.results["failed_tests"],
            "passed_tests": self.results["passed_tests"],
        }
