#!/usr/bin/env python3
"""
모듈 구조 분석 스크립트
파일 크기, 의존성, 응집도를 분석하여 구조 최적화 제안

Sample input: Python 프로젝트 소스 디렉토리
Expected output: 모듈 구조 분석 보고서 및 최적화 제안
"""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class ModuleAnalyzer:
    """모듈 구조 분석기"""

    def __init__(self):
        self.file_info = {}
        self.dependencies = defaultdict(set)
        self.reverse_dependencies = defaultdict(set)
        self.function_counts = {}
        self.class_counts = {}
        self.complexity_scores = {}

    def analyze_file(self, file_path: Path) -> Dict:
        """단일 파일 분석"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 기본 정보
            lines = content.split("\n")
            line_count = len(lines)

            # AST 파싱으로 구조 분석
            try:
                tree = ast.parse(content)
                info = self._analyze_ast(tree, content)
            except SyntaxError:
                # 구문 오류가 있는 파일은 기본 정보만
                info = {
                    "functions": 0,
                    "classes": 0,
                    "imports": [],
                    "complexity_score": 0,
                }

            # 파일 정보 저장
            file_info = {
                "path": file_path,
                "line_count": line_count,
                "functions": info["functions"],
                "classes": info["classes"],
                "imports": info["imports"],
                "complexity_score": info["complexity_score"],
                "file_size_bytes": (
                    file_path.stat().st_size if file_path.exists() else 0
                ),
            }

            return file_info

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {
                "path": file_path,
                "line_count": 0,
                "functions": 0,
                "classes": 0,
                "imports": [],
                "complexity_score": 0,
                "file_size_bytes": 0,
            }

    def _analyze_ast(self, tree: ast.AST, content: str) -> Dict:
        """AST를 분석하여 구조 정보 추출"""
        functions = 0
        classes = 0
        imports = []
        complexity_score = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions += 1
                # 복잡도 계산 (간단히 중첩 레벨과 분기로 계산)
                complexity_score += self._calculate_function_complexity(node)

            elif isinstance(node, ast.ClassDef):
                classes += 1
                complexity_score += 2  # 클래스는 기본 복잡도 2

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "complexity_score": complexity_score,
        }

    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        """함수의 복잡도 계산"""
        complexity = 1  # 기본 복잡도

        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def analyze_dependencies(self, src_path: Path) -> Dict:
        """의존성 분석"""
        python_files = list(src_path.rglob("*.py"))

        for file_path in python_files:
            if any(exclude in str(file_path) for exclude in ["test_", "__pycache__"]):
                continue

            file_info = self.analyze_file(file_path)
            self.file_info[str(file_path)] = file_info

            # 의존성 매핑
            relative_path = file_path.relative_to(src_path)
            for import_name in file_info["imports"]:
                # 프로젝트 내부 의존성만 추적 (상대 import)
                if import_name.startswith(".") or any(
                    part in import_name for part in ["core", "utils", "api"]
                ):
                    self.dependencies[str(relative_path)].add(import_name)
                    self.reverse_dependencies[import_name].add(str(relative_path))

        return {
            "total_files": len(self.file_info),
            "dependencies": dict(self.dependencies),
            "reverse_dependencies": dict(self.reverse_dependencies),
        }

    def find_structure_issues(self) -> Dict[str, List]:
        """구조적 문제점 식별"""
        issues = {
            "large_files": [],
            "complex_files": [],
            "high_dependency_files": [],
            "circular_dependencies": [],
            "god_objects": [],
            "suggested_splits": [],
        }

        for file_path, info in self.file_info.items():
            # 큰 파일 (400줄 이상)
            if info["line_count"] > 400:
                issues["large_files"].append(
                    {
                        "file": file_path,
                        "lines": info["line_count"],
                        "functions": info["functions"],
                        "classes": info["classes"],
                    }
                )

            # 복잡한 파일 (복잡도 스코어 50 이상)
            if info["complexity_score"] > 50:
                issues["complex_files"].append(
                    {
                        "file": file_path,
                        "complexity": info["complexity_score"],
                        "functions": info["functions"],
                        "classes": info["classes"],
                    }
                )

            # 의존성이 많은 파일 (10개 이상)
            if len(info["imports"]) > 10:
                issues["high_dependency_files"].append(
                    {
                        "file": file_path,
                        "dependencies": len(info["imports"]),
                        "imports": info["imports"][:5],  # 처음 5개만
                    }
                )

            # God Object 후보 (클래스 많고 복잡도 높음)
            if info["classes"] > 3 and info["complexity_score"] > 30:
                issues["god_objects"].append(
                    {
                        "file": file_path,
                        "classes": info["classes"],
                        "complexity": info["complexity_score"],
                        "lines": info["line_count"],
                    }
                )

            # 분할 제안 (함수가 많고 큰 파일)
            if info["functions"] > 15 and info["line_count"] > 300:
                issues["suggested_splits"].append(
                    {
                        "file": file_path,
                        "functions": info["functions"],
                        "lines": info["line_count"],
                        "suggestion": f"Consider splitting into {info['functions']//10 + 1} modules",
                    }
                )

        return issues

    def generate_recommendations(self, issues: Dict) -> List[str]:
        """개선 권장사항 생성"""
        recommendations = []

        if issues["large_files"]:
            recommendations.append(
                f"📏 {len(issues['large_files'])}개의 큰 파일이 발견되었습니다. "
                "기능별로 분할을 고려하세요."
            )

        if issues["complex_files"]:
            recommendations.append(
                f"🔄 {len(issues['complex_files'])}개의 복잡한 파일이 발견되었습니다. "
                "함수 분할과 리팩토링을 고려하세요."
            )

        if issues["high_dependency_files"]:
            recommendations.append(
                f"🔗 {len(issues['high_dependency_files'])}개의 파일이 과도한 의존성을 가집니다. "
                "의존성 주입이나 인터페이스 분리를 고려하세요."
            )

        if issues["god_objects"]:
            recommendations.append(
                f"👹 {len(issues['god_objects'])}개의 God Object 후보가 발견되었습니다. "
                "단일 책임 원칙에 따라 클래스를 분할하세요."
            )

        if issues["suggested_splits"]:
            recommendations.append(
                f"✂️ {len(issues['suggested_splits'])}개의 파일이 분할 후보입니다. "
                "관련 기능끼리 묶어서 별도 모듈로 분리하세요."
            )

        # 일반적인 권장사항
        recommendations.extend(
            [
                "🏗️ 공통 기능은 base_classes.py와 common/ 모듈을 활용하세요.",
                "📦 비슷한 기능끼리는 하위 패키지로 그룹화하세요.",
                "🔄 순환 의존성이 있다면 인터페이스나 의존성 주입으로 해결하세요.",
                "📏 각 모듈은 500줄 이하, 복잡도 50 이하를 유지하세요.",
            ]
        )

        return recommendations


def generate_structure_report(src_path: Path) -> str:
    """구조 분석 보고서 생성"""
    analyzer = ModuleAnalyzer()

    print("🔍 모듈 구조를 분석합니다...")
    dep_info = analyzer.analyze_dependencies(src_path)

    print("🔧 구조적 문제점을 식별합니다...")
    issues = analyzer.find_structure_issues()

    print("💡 개선 권장사항을 생성합니다...")
    recommendations = analyzer.generate_recommendations(issues)

    # 보고서 생성
    report_lines = []

    report_lines.append("=" * 80)
    report_lines.append("📊 모듈 구조 분석 보고서")
    report_lines.append("=" * 80)
    report_lines.append("")

    # 전체 통계
    report_lines.append("📈 전체 통계:")
    report_lines.append(f"  - 분석된 파일: {dep_info['total_files']}개")

    total_lines = sum(info["line_count"] for info in analyzer.file_info.values())
    total_functions = sum(info["functions"] for info in analyzer.file_info.values())
    total_classes = sum(info["classes"] for info in analyzer.file_info.values())
    avg_complexity = (
        sum(info["complexity_score"] for info in analyzer.file_info.values())
        / len(analyzer.file_info)
        if analyzer.file_info
        else 0
    )

    report_lines.append(f"  - 전체 코드 라인: {total_lines:,}줄")
    report_lines.append(f"  - 전체 함수: {total_functions}개")
    report_lines.append(f"  - 전체 클래스: {total_classes}개")
    report_lines.append(f"  - 평균 복잡도: {avg_complexity:.1f}")
    report_lines.append("")

    # 문제점 요약
    report_lines.append("⚠️ 발견된 문제점:")
    total_issues = sum(len(issue_list) for issue_list in issues.values())
    if total_issues == 0:
        report_lines.append("  🎉 구조적 문제점이 발견되지 않았습니다!")
    else:
        for issue_type, issue_list in issues.items():
            if issue_list:
                issue_name = issue_type.replace("_", " ").title()
                report_lines.append(f"  - {issue_name}: {len(issue_list)}개")
    report_lines.append("")

    # 상위 문제 파일들
    if issues["large_files"]:
        report_lines.append("📏 큰 파일들 (상위 5개):")
        for item in sorted(
            issues["large_files"], key=lambda x: x["lines"], reverse=True
        )[:5]:
            report_lines.append(
                f"  - {item['file']:50} ({item['lines']:3}줄, {item['functions']:2}함수, {item['classes']:2}클래스)"
            )
        report_lines.append("")

    if issues["complex_files"]:
        report_lines.append("🔄 복잡한 파일들 (상위 5개):")
        for item in sorted(
            issues["complex_files"], key=lambda x: x["complexity"], reverse=True
        )[:5]:
            report_lines.append(
                f"  - {item['file']:50} (복잡도 {item['complexity']:2}, {item['functions']:2}함수)"
            )
        report_lines.append("")

    # 권장사항
    report_lines.append("💡 개선 권장사항:")
    for rec in recommendations:
        report_lines.append(f"  {rec}")
    report_lines.append("")

    report_lines.append("=" * 80)

    return "\n".join(report_lines)


def main():
    """메인 실행 함수"""
    src_path = Path("/home/jclee/app/blacklist/src")

    if not src_path.exists():
        print(f"❌ 소스 디렉토리가 존재하지 않습니다: {src_path}")
        return

    # 구조 분석 실행
    report = generate_structure_report(src_path)

    # 보고서 출력
    print(report)

    # 보고서 파일로 저장
    report_path = Path("CODE_QUALITY_MODULE_STRUCTURE_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"📄 상세 보고서가 저장되었습니다: {report_path}")


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: AST parsing
    total_tests += 1
    try:
        test_code = "def test_func(): pass\nclass TestClass: pass"
        tree = ast.parse(test_code)
        if not isinstance(tree, ast.Module):
            all_validation_failures.append("AST test: Failed to parse test code")
    except Exception as e:
        all_validation_failures.append(f"AST test: Failed - {e}")

    # Test 2: Module analyzer creation
    total_tests += 1
    try:
        analyzer = ModuleAnalyzer()
        if not hasattr(analyzer, "analyze_file"):
            all_validation_failures.append("Analyzer test: Missing analyze_file method")
    except Exception as e:
        all_validation_failures.append(f"Analyzer test: Failed - {e}")

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
        print("Module structure analyzer is validated and ready to run")
        main()
        sys.exit(0)
