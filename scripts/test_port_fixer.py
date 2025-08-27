#!/usr/bin/env python3
"""
Test Port Configuration Fixer - Real Automation System v11.1
테스트 포트 설정 모순 제거 도구

This script fixes hardcoded port 2542 references in tests to use the correct Docker port 32542.
"""

import os
import re
from pathlib import Path


def fix_port_in_file(file_path, old_port="2542", new_port="32542"):
    """Fix port references in a specific file"""
    if not file_path.exists():
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Skip the test that specifically tests for port 2542
        if (
            'assert port == "2542"' in content
            and "test_final_coverage_refactored.py" in str(file_path)
        ):
            print(f"  ⚠️ Skipped {file_path} (contains specific port assertion test)")
            return False

        # Patterns to fix
        patterns = [
            (rf"localhost:{old_port}", f"localhost:{new_port}"),
            (rf"http://localhost:{old_port}", f"http://localhost:{new_port}"),
            (rf'"http://localhost:{old_port}"', f'"http://localhost:{new_port}"'),
            (
                rf'BASE_URL = "http://localhost:{old_port}"',
                f'BASE_URL = "http://localhost:{new_port}"',
            ),
            (
                rf'base_url = "http://localhost:{old_port}"',
                f'base_url = "http://localhost:{new_port}"',
            ),
        ]

        updated_content = content
        changes_made = False

        for old_pattern, new_pattern in patterns:
            if re.search(old_pattern, updated_content):
                updated_content = re.sub(old_pattern, new_pattern, updated_content)
                changes_made = True

        # Special case for port lists (only add 32542 if not already present)
        if "valid_ports" in content and old_port in content:
            if new_port not in content:
                # Add the correct port to valid ports list
                updated_content = re.sub(
                    r"valid_ports = \[([^]]*)\]",
                    f"valid_ports = [\\1, {new_port}]",
                    updated_content,
                )
                changes_made = True

        if changes_made:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            return True

        return False

    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False


def main():
    """Main test port fixer"""
    print("🔧 테스트 포트 설정 수정 시작 - Real Automation System v11.1")
    print("=" * 60)
    print("📍 포트 2542 → 32542 (Docker 환경에 맞춤)")

    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"

    if not tests_dir.exists():
        print("❌ Tests directory not found")
        return

    fixed_files = []
    total_files = 0

    # Find all Python test files
    test_files = list(tests_dir.rglob("*.py"))

    for test_file in test_files:
        total_files += 1
        if fix_port_in_file(test_file):
            fixed_files.append(str(test_file.relative_to(project_root)))
            print(f"  ✅ Fixed: {test_file.relative_to(project_root)}")

    print("\n" + "=" * 60)
    print("📊 테스트 포트 수정 결과:")
    print(f"📁 총 테스트 파일: {total_files}개")
    print(f"🔄 수정된 파일: {len(fixed_files)}개")

    if fixed_files:
        print("\n📝 수정된 파일들:")
        for file in fixed_files:
            print(f"  - {file}")

        print("\n🤖 Git 커밋 생성...")
        os.chdir(project_root)
        os.system("git add tests/")
        commit_message = """fix: update test port configuration from 2542 to 32542

🤖 Real Automation System v11.1 - Test Port Fix
- 테스트에서 하드코딩된 포트 2542를 Docker 포트 32542로 수정
- 실제 서비스 포트와 테스트 포트 일치시킴

Files updated: """ + ", ".join(
            fixed_files
        )

        os.system(f'git commit -m "{commit_message}"')
        print("✅ Git 커밋 완료")
    else:
        print("ℹ️ 수정이 필요한 파일이 없습니다")

    print(f"\n🎯 테스트 포트 설정 수정 완료!")

    # Now create a test configuration to handle both ports dynamically
    create_dynamic_port_config(project_root)


def create_dynamic_port_config(project_root):
    """Create a dynamic port configuration for tests"""
    config_content = '''"""
Dynamic Test Port Configuration
Automatically detects running service port for tests
"""

import os
import requests
from typing import Optional

def detect_service_port() -> int:
    """Detect which port the service is running on"""
    # Common ports to check
    ports_to_check = [32542, 2542, 8080, 3000]
    
    for port in ports_to_check:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=2)
            if response.status_code == 200:
                return port
        except:
            continue
    
    # Default to Docker port if none detected
    return 32542

def get_test_base_url() -> str:
    """Get the base URL for tests"""
    port = detect_service_port()
    return f"http://localhost:{port}"

# Global configuration
TEST_SERVICE_PORT = detect_service_port()
TEST_BASE_URL = get_test_base_url()
'''

    config_file = project_root / "tests" / "test_port_config.py"
    with open(config_file, "w") as f:
        f.write(config_content)

    print(f"✅ 동적 포트 설정 파일 생성: {config_file.relative_to(project_root)}")


if __name__ == "__main__":
    main()
