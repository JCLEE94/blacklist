#!/usr/bin/env python3
"""
오프라인 패키지 빌더 - 종속성 관리
"""

import sys
import subprocess
import shutil
from pathlib import Path
from .base import OfflinePackageBase


class DependencyManager(OfflinePackageBase):
    """Python 종속성 관리 클래스"""
    
    def collect_python_dependencies(self):
        """Python 종속성 수집"""
        self.log_progress("Collecting Python dependencies...")
        
        requirements_files = [
            self.project_root / "config" / "requirements.txt",
            self.project_root / "config" / "requirements-dev.txt"
        ]
        
        pip_dir = self.dirs["dependencies"] / "pip"
        pip_dir.mkdir(exist_ok=True)
        
        for req_file in requirements_files:
            if req_file.exists():
                self._download_pip_packages(req_file, pip_dir)
                print(f"   ✓ Processed {req_file.name}")
        
        # requirements.txt 복사
        for req_file in requirements_files:
            if req_file.exists():
                shutil.copy2(req_file, self.dirs["configs"])
        
        self.log_progress("Python dependencies collected", "python_deps")
    
    def _download_pip_packages(self, requirements_file: Path, output_dir: Path):
        """pip 패키지 다운로드"""
        try:
            cmd = [
                sys.executable, "-m", "pip", "download",
                "-r", str(requirements_file),
                "-d", str(output_dir),
                "--platform", "linux_x86_64",
                "--only-binary=:all:",
                "--no-deps"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"   ⚠️  Warning: Some packages failed to download")
                print(f"   Error: {result.stderr}")
            
        except Exception as e:
            print(f"   ❌ Failed to download packages: {e}")
    
    def collect_system_dependencies(self):
        """시스템 종속성 수집 (Ubuntu/Debian)"""
        self.log_progress("Collecting system dependencies...")
        
        # 필수 시스템 패키지 목록
        system_packages = [
            "python3", "python3-pip", "python3-venv",
            "docker.io", "docker-compose",
            "redis-server", "sqlite3",
            "curl", "wget", "unzip"
        ]
        
        # apt 패키지 다운로드 시도
        apt_dir = self.dirs["dependencies"] / "apt"
        apt_dir.mkdir(exist_ok=True)
        
        self._create_package_list(system_packages, apt_dir)
        self.log_progress("System dependencies listed", "system_deps")
    
    def _create_package_list(self, packages: list, output_dir: Path):
        """패키지 목록 파일 생성"""
        package_list_file = output_dir / "required_packages.txt"
        
        with open(package_list_file, 'w') as f:
            f.write("# Required system packages for offline installation\n")
            f.write("# Install with: sudo apt install $(cat required_packages.txt)\n\n")
            for package in packages:
                f.write(f"{package}\n")
        
        print(f"   ✓ Package list created: {package_list_file}")