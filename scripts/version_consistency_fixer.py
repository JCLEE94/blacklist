#!/usr/bin/env python3
"""
Version Consistency Fixer - Real Automation System v11.1
버전 정보 모순 제거 도구

This script resolves all version inconsistencies across the project
by using version_info.json as the single source of truth.
"""

import json
import os
import re
import sys
from pathlib import Path


def load_version_info():
    """Load the authoritative version from version_info.json"""
    version_file = Path(__file__).parent.parent / "version_info.json"

    if not version_file.exists():
        print("❌ version_info.json not found. Generating from git...")
        # Get git commit count as version
        import subprocess

        try:
            count = (
                subprocess.check_output(["git", "rev-list", "--count", "HEAD"])
                .decode()
                .strip()
            )
            hash_short = (
                subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
                .decode()
                .strip()
            )
            version = f"1.0.{count}"

            version_info = {
                "version": version,
                "build_timestamp": "2025-08-27T23:20:00.000000",
                "git_commit_count": int(count),
                "git_commit_hash": hash_short,
                "automated": True,
                "automation_system": "Real Automation System v11.1 with ThinkMCP - Version Fixer",
                "watchtower_enabled": True,
                "cicd_pipeline": "active",
            }

            with open(version_file, "w") as f:
                json.dump(version_info, f, indent=2)
            print(f"✅ Generated version_info.json with version {version}")
        except Exception as e:
            print(f"❌ Failed to generate version from git: {e}")
            return None

    with open(version_file, "r") as f:
        return json.load(f)


def update_file_version(file_path, old_version_pattern, new_version, description=""):
    """Update version in a specific file"""
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find and replace version patterns
        updated_content = re.sub(old_version_pattern, new_version, content)

        if updated_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            print(f"✅ Updated {file_path} {description}")
            return True
        else:
            print(f"ℹ️ No changes needed in {file_path}")
            return False
    except Exception as e:
        print(f"❌ Failed to update {file_path}: {e}")
        return False


def main():
    """Main version consistency fixer"""
    print("🔧 버전 정보 모순 제거 시작 - Real Automation System v11.1")
    print("=" * 60)

    # Load authoritative version
    version_info = load_version_info()
    if not version_info:
        print("❌ Could not determine authoritative version")
        sys.exit(1)

    authoritative_version = version_info["version"]
    print(f"📌 권위 있는 버전: {authoritative_version}")

    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    updates_made = []

    # 1. Update config/VERSION
    version_file = project_root / "config" / "VERSION"
    if update_file_version(
        version_file, r"^\d+\.\d+\.\d+.*$", authoritative_version, "(main VERSION file)"
    ):
        updates_made.append("config/VERSION")

    # 2. Update package.json
    package_file = project_root / "package.json"
    if update_file_version(
        package_file,
        r'"version":\s*"[^"]*"',
        f'"version": "{authoritative_version}"',
        "(package.json)",
    ):
        updates_made.append("package.json")

    # 3. Update API OpenAPI spec
    openapi_file = project_root / "api" / "openapi" / "blacklist-api.yaml"
    if update_file_version(
        openapi_file,
        r"version:\s*\d+\.\d+\.\d+",
        f"version: {authoritative_version}",
        "(OpenAPI spec)",
    ):
        updates_made.append("api/openapi/blacklist-api.yaml")

    # 4. Update Makefile VERSION reference
    makefile = project_root / "Makefile"
    if update_file_version(
        makefile,
        r"VERSION \?\= \$\(shell cat config/VERSION.*\)",
        f'VERSION ?= $(shell cat config/VERSION 2>/dev/null || echo "{authoritative_version}")',
        "(Makefile)",
    ):
        updates_made.append("Makefile")

    # 5. Find and update Python files with hardcoded versions
    python_files_to_check = [
        "tests/__init__.py",
        "src/core/main.py",
        "src/core/app_compact.py",
    ]

    for py_file in python_files_to_check:
        full_path = project_root / py_file
        if update_file_version(
            full_path,
            r'__version__\s*=\s*["\'][^"\']*["\']',
            f'__version__ = "{authoritative_version}"',
            f"({py_file})",
        ):
            updates_made.append(py_file)

    # 6. Update chart version
    chart_file = project_root / "charts" / "blacklist" / "Chart.yaml"
    if update_file_version(
        chart_file,
        r"version:\s*\d+\.\d+\.\d+",
        f"version: {authoritative_version}",
        "(Helm Chart version)",
    ):
        updates_made.append("charts/blacklist/Chart.yaml")

    if update_file_version(
        chart_file,
        r'appVersion:\s*["\']?[^"\']*["\']?',
        f'appVersion: "{authoritative_version}"',
        "(Helm Chart appVersion)",
    ):
        updates_made.append("charts/blacklist/Chart.yaml (appVersion)")

    # Summary
    print("\n" + "=" * 60)
    print("📊 버전 일관성 수정 결과:")
    print(f"✅ 표준 버전: {authoritative_version}")
    print(f"🔄 업데이트된 파일: {len(updates_made)}개")

    if updates_made:
        print("\n📝 수정된 파일들:")
        for file in updates_made:
            print(f"  - {file}")

        print("\n🤖 Git 커밋 준비 중...")
        os.system("git add -A")
        commit_message = f"fix: resolve version inconsistencies to {authoritative_version}\n\n🤖 Real Automation System v11.1 - Version Consistency Fix\n- 모든 버전 참조를 {authoritative_version}로 통일\n- version_info.json을 단일 진실 소스로 사용\n\nFiles updated: {', '.join(updates_made)}"

        os.system(f'git commit -m "{commit_message}"')
        print("✅ Git 커밋 완료")
    else:
        print("ℹ️ 모든 버전이 이미 일관됨")

    print(f"\n🎯 버전 정보 모순 제거 완료: {authoritative_version}")


if __name__ == "__main__":
    main()
