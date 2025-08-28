#!/usr/bin/env python3
"""
__init__ 패턴 분석 전용 스크립트
실제 리팩토링 없이 패턴만 분석하여 보고서 생성

Sample input: Python 소스 파일들
Expected output: 중복 패턴 분석 보고서
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


class InitPatternAnalyzer:
    """__init__ 패턴 분석기"""

    def __init__(self):
        self.patterns = {
            "db_path_assignment": r"self\.db_path\s*=\s*db_path",
            "service_name_assignment": r"self\.service_name\s*=\s*service_name",
            "logger_creation": r"self\.logger\s*=\s*logging\.getLogger",
            "timestamp_creation": r"self\.(?:created_at|updated_at)\s*=\s*datetime\.now",
            "config_assignment": r"self\.\w+\s*=\s*\w+",
            "sqlite_connection": r"sqlite3\.connect",
            "super_init_call": r"super\(\)\.__init__",
            "flask_app_creation": r"Flask\(__name__\)",
            "thread_lock_creation": r"threading\.Lock\(\)",
            "default_parameter": r"def __init__\(.*=.*\)",
        }

        self.pattern_categories = {
            "database": ["db_path_assignment", "sqlite_connection"],
            "service": ["service_name_assignment", "logger_creation"],
            "timestamp": ["timestamp_creation"],
            "configuration": ["config_assignment"],
            "inheritance": ["super_init_call"],
            "web": ["flask_app_creation"],
            "threading": ["thread_lock_creation"],
            "parameters": ["default_parameter"],
        }

    def analyze_file(self, file_path: Path) -> Dict[str, List[str]]:
        """파일에서 __init__ 패턴을 분석"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # __init__ 메소드 찾기
            init_pattern = r"def __init__\(.*?\):(.*?)(?=def |\nclass |\Z)"
            init_methods = re.findall(init_pattern, content, re.DOTALL)

            found_patterns = {}
            for pattern_name, pattern_regex in self.patterns.items():
                matches = []
                for init_content in init_methods:
                    if re.search(pattern_regex, init_content):
                        # 매치된 줄만 추출 (간단히)
                        lines = init_content.split("\n")
                        matched_lines = [
                            line.strip()
                            for line in lines
                            if re.search(pattern_regex, line)
                        ]
                        matches.extend(matched_lines)

                if matches:
                    found_patterns[pattern_name] = matches

            return found_patterns

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {}

    def get_pattern_category(self, pattern_name: str) -> str:
        """패턴의 카테고리를 반환"""
        for category, patterns in self.pattern_categories.items():
            if pattern_name in patterns:
                return category
        return "other"


def analyze_codebase(src_path: Path) -> Dict[str, any]:
    """전체 코드베이스 분석"""
    analyzer = InitPatternAnalyzer()

    # Python 파일들 찾기
    python_files = list(src_path.rglob("*.py"))

    # 분석 결과 저장
    all_patterns = defaultdict(list)
    file_pattern_map = {}
    pattern_frequency = Counter()
    category_frequency = Counter()

    print(f"🔍 분석 중: {len(python_files)}개 Python 파일...")

    for file_path in python_files:
        # 테스트 파일과 특정 파일들 제외
        if any(
            exclude in str(file_path) for exclude in ["test_", "__pycache__", ".pyc"]
        ):
            continue

        patterns = analyzer.analyze_file(file_path)
        if patterns:
            relative_path = file_path.relative_to(src_path)
            file_pattern_map[str(relative_path)] = patterns

            for pattern_name, matches in patterns.items():
                all_patterns[pattern_name].extend(matches)
                pattern_frequency[pattern_name] += len(matches)

                category = analyzer.get_pattern_category(pattern_name)
                category_frequency[category] += len(matches)

    return {
        "total_files": len(python_files),
        "files_with_patterns": len(file_pattern_map),
        "file_pattern_map": file_pattern_map,
        "all_patterns": dict(all_patterns),
        "pattern_frequency": dict(pattern_frequency),
        "category_frequency": dict(category_frequency),
        "analyzer": analyzer,
    }


def generate_report(analysis_results: Dict[str, any]) -> str:
    """분석 결과 보고서 생성"""
    report_lines = []

    report_lines.append("=" * 80)
    report_lines.append("📊 __init__ 패턴 분석 보고서")
    report_lines.append("=" * 80)
    report_lines.append("")

    # 전체 통계
    report_lines.append("📈 전체 통계:")
    report_lines.append(f"  - 전체 Python 파일: {analysis_results['total_files']}개")
    report_lines.append(f"  - 패턴이 발견된 파일: {analysis_results['files_with_patterns']}개")
    report_lines.append(
        f"  - 분석 비율: {analysis_results['files_with_patterns']/analysis_results['total_files']*100:.1f}%"
    )
    report_lines.append("")

    # 카테고리별 빈도
    report_lines.append("📋 카테고리별 패턴 빈도:")
    for category, count in sorted(
        analysis_results["category_frequency"].items(), key=lambda x: x[1], reverse=True
    ):
        report_lines.append(f"  - {category:12}: {count:3}개")
    report_lines.append("")

    # 패턴별 상세 빈도
    report_lines.append("🔍 패턴별 상세 빈도:")
    for pattern, count in sorted(
        analysis_results["pattern_frequency"].items(), key=lambda x: x[1], reverse=True
    ):
        category = analysis_results["analyzer"].get_pattern_category(pattern)
        report_lines.append(f"  - {pattern:25} ({category:10}): {count:3}개")
    report_lines.append("")

    # 중복도가 높은 파일들
    report_lines.append("🎯 중복도가 높은 파일들 (3개 이상 패턴):")
    high_duplicate_files = []
    for file_path, patterns in analysis_results["file_pattern_map"].items():
        if len(patterns) >= 3:
            total_occurrences = sum(len(matches) for matches in patterns.values())
            high_duplicate_files.append((file_path, len(patterns), total_occurrences))

    high_duplicate_files.sort(key=lambda x: x[2], reverse=True)

    for file_path, pattern_count, total_occurrences in high_duplicate_files[:10]:
        report_lines.append(
            f"  - {file_path:50} ({pattern_count}개 패턴, {total_occurrences}회 출현)"
        )
    report_lines.append("")

    # 리팩토링 권장사항
    report_lines.append("💡 리팩토링 권장사항:")

    db_pattern_count = analysis_results["category_frequency"].get("database", 0)
    service_pattern_count = analysis_results["category_frequency"].get("service", 0)
    timestamp_pattern_count = analysis_results["category_frequency"].get("timestamp", 0)

    if db_pattern_count > 10:
        report_lines.append(f"  ✅ DatabaseMixin 도입 권장 (현재 {db_pattern_count}개 중복)")

    if service_pattern_count > 15:
        report_lines.append(
            f"  ✅ BaseService 클래스 도입 권장 (현재 {service_pattern_count}개 중복)"
        )

    if timestamp_pattern_count > 5:
        report_lines.append(
            f"  ✅ TimestampMixin 도입 권장 (현재 {timestamp_pattern_count}개 중복)"
        )

    if len(high_duplicate_files) > 0:
        report_lines.append(f"  ✅ {len(high_duplicate_files)}개 파일이 중복 리팩토링 대상")

    report_lines.append("")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)


def main():
    """메인 실행 함수"""
    src_path = Path("/home/jclee/app/blacklist/src")

    if not src_path.exists():
        print(f"❌ 소스 디렉토리가 존재하지 않습니다: {src_path}")
        return

    # 분석 실행
    print("🚀 __init__ 패턴 분석을 시작합니다...")
    analysis_results = analyze_codebase(src_path)

    # 보고서 생성
    report = generate_report(analysis_results)

    # 보고서 출력
    print(report)

    # 보고서 파일로 저장
    report_path = Path("CODE_QUALITY_INIT_PATTERNS_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"📄 상세 보고서가 저장되었습니다: {report_path}")


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Pattern definitions
    total_tests += 1
    try:
        analyzer = InitPatternAnalyzer()
        if len(analyzer.patterns) < 5:
            all_validation_failures.append(
                "Pattern test: Insufficient patterns defined"
            )
    except Exception as e:
        all_validation_failures.append(f"Pattern test: Failed to create analyzer - {e}")

    # Test 2: Category mapping
    total_tests += 1
    try:
        analyzer = InitPatternAnalyzer()
        category = analyzer.get_pattern_category("db_path_assignment")
        if category != "database":
            all_validation_failures.append("Category test: Wrong category mapping")
    except Exception as e:
        all_validation_failures.append(f"Category test: Failed - {e}")

    # Test 3: Source path existence
    total_tests += 1
    try:
        src_path = Path("/home/jclee/app/blacklist/src")
        if not src_path.exists():
            all_validation_failures.append("Path test: Source directory does not exist")
    except Exception as e:
        all_validation_failures.append(f"Path test: Failed - {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Pattern analyzer is validated and ready to run")
        main()
        sys.exit(0)
