"""
Python 의존성 관리자

Python 의존성 수집, 패키지들의 오프라인 다운로드 및 설치 스크립트 생성을 담당합니다.
"""

import sys
import json
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent


class PythonDependencyManager:
    """오프라인 패키지용 Python 의존성 관리자"""
    
    def __init__(self, deps_dir: Path):
        self.deps_dir = deps_dir
    
    def collect_dependencies(self, manifest: Dict[str, Any]):
        """전체 Python 의존성 수집 프로세스"""
        print("\n🐍 Python 의존성 수집 중...")
        
        try:
            # requirements 파일들 처리
            req_files = self._find_requirements_files()
            
            # wheels 다운로드
            wheels_count = self._download_wheels(req_files)
            
            # 의존성 정보 저장
            self._save_dependencies_info(req_files)
            
            # 설치 스크립트 생성
            self._create_install_script()
            
            # 매니페스트 업데이트
            manifest["components"]["python_dependencies"] = {
                "status": "success",
                "wheels_count": wheels_count,
                "info_file": "dependencies/dependencies-info.json"
            }
            
        except Exception as e:
            print(f"  ❌ Python 의존성 수집 실패: {e}")
            manifest["components"]["python_dependencies"] = {
                "status": "failed",
                "error": str(e)
            }
    
    def _find_requirements_files(self) -> list:
        """사용 가능한 requirements 파일 찾기"""
        potential_files = [
            PROJECT_ROOT / "requirements.txt",
            PROJECT_ROOT / "requirements-dev.txt"
        ]
        
        return [f for f in potential_files if f.exists()]
    
    def _download_wheels(self, req_files: list) -> int:
        """
wheels 다운로드"""
        wheels_dir = self.deps_dir / "all_wheels"
        wheels_dir.mkdir(parents=True, exist_ok=True)
        
        total_wheels = 0
        
        for req_file in req_files:
            print(f"  📄 처리 중: {req_file.name}")
            
            # 전체 의존성 패키지 다운로드 (재귀적)
            download_cmd = [
                sys.executable, "-m", "pip", "download",
                "-r", str(req_file),
                "-d", str(wheels_dir),
                "--platform", "linux_x86_64",
                "--only-binary=:all:",
                "--python-version", "3.9"
            ]
            
            result = subprocess.run(download_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                wheels_count = len(list(wheels_dir.glob("*.whl")))
                print(f"    ✅ {req_file.name} 다운로드 완료 ({wheels_count} 파일)")
                total_wheels = max(total_wheels, wheels_count)
            else:
                print(f"    ⚠️ {req_file.name} 다운로드 실패: {result.stderr}")
        
        # pip freeze로 고정된 의존성 생성
        self._create_frozen_requirements()
        
        return total_wheels
    
    def _create_frozen_requirements(self):
        """고정된 requirements 파일 생성"""
        print("  🔗 의존성 트리 생성 중...")
        
        pip_freeze_cmd = [sys.executable, "-m", "pip", "freeze"]
        result = subprocess.run(pip_freeze_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            freeze_file = self.deps_dir / "requirements-frozen.txt"
            with open(freeze_file, 'w') as f:
                f.write(result.stdout)
            print(f"    ✅ 고정된 의존성 저장: {freeze_file}")
    
    def _save_dependencies_info(self, req_files: list):
        """의존성 메타데이터 저장"""
        deps_info = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "requirements_files": [str(f.name) for f in req_files],
            "download_date": datetime.now().isoformat()
        }
        
        info_file = self.deps_dir / "dependencies-info.json"
        with open(info_file, 'w') as f:
            json.dump(deps_info, f, indent=2)
    
    def _create_install_script(self):
        """오프라인 설치 스크립트 생성"""
        script_content = '''#!/bin/bash
# Python 의존성 오프라인 설치 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
DEPS_DIR="$PACKAGE_ROOT/dependencies"

if [[ ! -d "$DEPS_DIR" ]]; then
    echo "❌ 의존성 디렉토리가 없습니다: $DEPS_DIR"
    exit 1
fi

echo "🐍 Python 의존성 설치 중..."

# pip 업그레이드 (오프라인)
if [[ -f "$DEPS_DIR/all_wheels/pip"*.whl ]]; then
    python3 -m pip install --no-index --find-links "$DEPS_DIR/all_wheels" --upgrade pip
fi

# 모든 wheels 설치
echo "  📦 패키지 설치 중..."
python3 -m pip install --no-index --find-links "$DEPS_DIR/all_wheels" --requirement "$DEPS_DIR/requirements-frozen.txt"

echo "✅ Python 의존성 설치 완료"

# 설치된 패키지 확인
echo "📋 설치된 패키지:"
python3 -m pip list
'''
        
        # 스크립트 디렉토리는 비어있을 수 있으므로 생성
        scripts_dir = self.deps_dir.parent / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        python_script = scripts_dir / "install-python-deps.sh"
        with open(python_script, 'w') as f:
            f.write(script_content)
        python_script.chmod(0o755)
