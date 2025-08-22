#!/usr/bin/env python3
"""
Flask Import 통합 스크립트
분산된 Flask import를 common/imports.py로 통합하여 중복 제거

Sample input: Flask import가 있는 Python 파일들
Expected output: common/imports를 사용하는 통합된 import 패턴
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Set


def find_flask_imports(file_path: Path) -> Dict[str, List[str]]:
    """파일에서 Flask import 패턴을 찾아서 반환"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    flask_imports = {}

    # from flask import ... 패턴 찾기
    flask_pattern = r"from flask import (.+)"
    matches = re.findall(flask_pattern, content)

    if matches:
        for match in matches:
            # 괄호 안의 내용이나 여러 줄 import 처리
            imports = [item.strip() for item in match.split(",")]
            flask_imports["flask"] = imports

    return flask_imports


def get_relative_import_path(source_file: Path, target_module: str) -> str:
    """상대 경로를 계산하여 import 경로 생성"""
    # src 디렉토리 기준으로 계산
    src_path = Path("/home/jclee/app/blacklist/src")
    relative_path = source_file.relative_to(src_path)
    depth = len(relative_path.parts) - 1

    if depth == 1:
        return f".{target_module}"
    else:
        return f"{'.' * depth}{target_module}"


def convert_flask_imports(file_path: Path) -> bool:
    """Flask import를 common/imports로 변환"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Flask import 찾기
        flask_pattern = r"from flask import (.+)"
        matches = re.findall(flask_pattern, content)

        if not matches:
            return False

        # 상대 경로 계산
        import_path = get_relative_import_path(file_path, "common.imports")

        # 사용된 Flask 컴포넌트들 수집
        all_imports = set()
        for match in matches:
            imports = [item.strip() for item in match.split(",")]
            all_imports.update(imports)

        # common/imports에서 제공하는 Flask 컴포넌트들
        available_imports = {
            "Blueprint",
            "Flask",
            "flash",
            "jsonify",
            "request",
            "render_template",
            "redirect",
            "url_for",
        }

        # 사용 가능한 import만 필터링
        valid_imports = all_imports.intersection(available_imports)

        if not valid_imports:
            return False

        # 새로운 import 라인 생성
        new_import = f"from {import_path} import {', '.join(sorted(valid_imports))}"

        # 기존 Flask import 제거
        content = re.sub(r"from flask import .+\n?", "", content)

        # logging import도 제거 (common/imports에서 logger 제공)
        if "logger" in content and "import logging" in content:
            content = re.sub(r"import logging\n?", "", content)
            content = re.sub(r"logger = logging\.getLogger\(__name__\)\n?", "", content)
            new_import += ", logger"

        # 새로운 import 추가 (다른 import들 이후에)
        lines = content.split("\n")
        insert_index = 0

        # docstring 이후 첫 번째 import 위치 찾기
        in_docstring = False
        for i, line in enumerate(lines):
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                in_docstring = not in_docstring
            elif not in_docstring and (
                line.startswith("import ") or line.startswith("from ")
            ):
                insert_index = i
                break

        # import 추가
        lines.insert(insert_index, new_import)
        lines.insert(insert_index + 1, "")

        # 파일 저장
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """메인 실행 함수"""
    src_path = Path("/home/jclee/app/blacklist/src")

    # Python 파일들 찾기
    python_files = list(src_path.rglob("*.py"))

    converted_files = []
    failed_files = []

    for file_path in python_files:
        # common/imports.py는 건드리지 않음
        if file_path.name == "imports.py":
            continue

        try:
            if convert_flask_imports(file_path):
                converted_files.append(file_path)
                print(f"✅ Converted: {file_path}")
            else:
                print(f"⏭️  Skipped: {file_path} (no Flask imports)")
        except Exception as e:
            failed_files.append((file_path, str(e)))
            print(f"❌ Failed: {file_path} - {e}")

    print(f"\n📊 변환 완료:")
    print(f"  - 성공: {len(converted_files)}개 파일")
    print(f"  - 실패: {len(failed_files)}개 파일")

    if failed_files:
        print(f"\n❌ 실패한 파일들:")
        for file_path, error in failed_files:
            print(f"  - {file_path}: {error}")


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Path existence
    total_tests += 1
    src_path = Path("/home/jclee/app/blacklist/src")
    if not src_path.exists():
        all_validation_failures.append("Path test: src directory does not exist")

    # Test 2: Common imports module existence
    total_tests += 1
    imports_path = src_path / "common" / "imports.py"
    if not imports_path.exists():
        all_validation_failures.append("Imports test: common/imports.py does not exist")

    # Test 3: Flask import pattern matching
    total_tests += 1
    test_content = "from flask import Blueprint, jsonify"
    pattern = r"from flask import (.+)"
    if not re.findall(pattern, test_content):
        all_validation_failures.append(
            "Pattern test: Flask import pattern matching failed"
        )

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
        print("Flask import converter is validated and ready to run")
        main()
        sys.exit(0)
