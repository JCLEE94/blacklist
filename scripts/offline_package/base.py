#!/usr/bin/env python3
"""
오프라인 패키지 빌더 - 기본 클래스
"""

import os
import sys
import shutil
import platform
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class OfflinePackageBase:
    """오프라인 패키지 빌더 기본 클래스"""
    
    def __init__(self, output_dir: str = "dist", include_source: bool = True):
        self.output_dir = Path(output_dir)
        self.include_source = include_source
        self.project_root = Path(__file__).parent.parent.parent
        self.package_name = "blacklist-offline-package"
        self.version = "2.0.0"
        self.package_dir = self.output_dir / f"{self.package_name}-v{self.version}"
        
        self.manifest = {
            "name": self.package_name,
            "version": self.version,
            "created_at": datetime.now().isoformat(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "components": {}
        }
        
        # 필수 디렉토리 구조
        self.dirs = {
            "dependencies": self.package_dir / "dependencies",
            "docker_images": self.package_dir / "docker-images", 
            "source_code": self.package_dir / "source-code",
            "scripts": self.package_dir / "scripts",
            "configs": self.package_dir / "configs",
            "database": self.package_dir / "database",
            "docs": self.package_dir / "docs"
        }
    
    def setup_directories(self):
        """디렉토리 구조 생성"""
        print(f"📁 Setting up package directory: {self.package_dir}")
        
        # 이전 패키지 제거
        if self.package_dir.exists():
            shutil.rmtree(self.package_dir)
        
        # 디렉토리 생성
        for name, path in self.dirs.items():
            path.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ Created {name} directory")
    
    def log_progress(self, message: str, component: str = None):
        """진행 상황 로깅"""
        print(f"🔄 {message}")
        if component:
            self.manifest["components"][component] = {
                "processed_at": datetime.now().isoformat(),
                "status": "completed"
            }
    
    def validate_environment(self):
        """환경 검증"""
        print("🔍 Validating environment...")
        
        # Docker 확인
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✓ Docker available")
                return True
            else:
                print("   ❌ Docker not found")
                return False
        except FileNotFoundError:
            print("   ❌ Docker not installed")
            return False