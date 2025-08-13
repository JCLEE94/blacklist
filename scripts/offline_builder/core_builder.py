#!/usr/bin/env python3
"""
오프라인 패키지 빌더 코어 클래스

메인 패키지 빌드 프로세스와 디렉토리 구조 관리를 담당합니다.
"""

import os
import shutil
import tarfile
import json
import platform
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from .docker_manager import DockerImageManager
from .dependency_manager import PythonDependencyManager
from .script_generator import InstallationScriptGenerator
from .config_generator import ConfigurationGenerator

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent
PACKAGE_NAME = "blacklist-offline-package"
VERSION = "2.0.0"


class OfflinePackageBuilder:
    """오프라인 패키지 빌더 메인 클래스"""
    
    def __init__(self, output_dir: str = "dist", include_source: bool = True):
        self.output_dir = Path(output_dir)
        self.include_source = include_source
        self.package_dir = self.output_dir / f"{PACKAGE_NAME}-v{VERSION}"
        
        # 매니페스트 초기화
        self.manifest = {
            "name": PACKAGE_NAME,
            "version": VERSION,
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
            "docs": self.package_dir / "docs",
            "tools": self.package_dir / "tools"
        }
        
        # 전문 매니저 초기화
        self.docker_manager = DockerImageManager(self.dirs["docker_images"])
        self.dependency_manager = PythonDependencyManager(self.dirs["dependencies"])
        self.script_generator = InstallationScriptGenerator(self.dirs["scripts"])
        self.config_generator = ConfigurationGenerator(self.dirs["configs"])
    
    def create_directory_structure(self):
        """디렉토리 구조 생성"""
        print("📁 디렉토리 구조 생성 중...")
        
        # 출력 디렉토리 정리
        if self.package_dir.exists():
            shutil.rmtree(self.package_dir)
        
        # 디렉토리 생성
        for name, path in self.dirs.items():
            path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ {name}: {path}")
    
    def copy_source_code(self):
        """소스 코드 복사"""
        if not self.include_source:
            return
            
        print("\n📄 소스 코드 복사 중...")
        
        source_dir = self.dirs["source_code"]
        
        # 복사할 디렉토리/파일 목록
        items_to_copy = [
            "src", "tests", "scripts", "monitoring", "chart", "argocd",
            "main.py", "init_database.py", "requirements.txt", "requirements-dev.txt",
            "pytest.ini", "pyproject.toml", ".isort.cfg", "Dockerfile",
            "docker-compose.yml", "docker-compose.local.yml", "Makefile",
            "README.md", "CLAUDE.md", "VERSION"
        ]
        
        copied_items = []
        
        for item in items_to_copy:
            source_path = PROJECT_ROOT / item
            if source_path.exists():
                dest_path = source_dir / item
                
                try:
                    if source_path.is_dir():
                        shutil.copytree(source_path, dest_path, 
                                      ignore=shutil.ignore_patterns(
                                          '__pycache__', '*.pyc', '*.pyo', 
                                          '.pytest_cache', '.coverage',
                                          'node_modules', '.git'
                                      ))
                    else:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, dest_path)
                    
                    copied_items.append(item)
                    print(f"  ✅ 복사됨: {item}")
                    
                except Exception as e:
                    print(f"  ⚠️ {item} 복사 실패: {e}")
        
        # .env 템플릿 파일 생성
        self._create_env_template(source_dir)
        copied_items.append(".env.template")
        
        self.manifest["components"]["source_code"] = {
            "status": "success",
            "items_count": len(copied_items),
            "items": copied_items
        }
    
    def _create_env_template(self, source_dir: Path):
        """환경 변수 템플릿 파일 생성"""
        env_template = source_dir / ".env.template"
        with open(env_template, 'w') as f:
            f.write("""# 블랙리스트 시스템 환경 변수 설정
# 이 파일을 .env로 복사하고 실제 값으로 수정하세요

# 애플리케이션 설정
PORT=32542
FLASK_ENV=production
SECRET_KEY=change-this-secret-key
JWT_SECRET_KEY=change-this-jwt-secret

# 데이터베이스 설정
DATABASE_URL=sqlite:////app/instance/blacklist.db

# Redis 설정
REDIS_URL=redis://redis:6379/0

# 수집 설정
COLLECTION_ENABLED=true
FORCE_DISABLE_COLLECTION=false

# 외부 서비스 자격증명
REGTECH_USERNAME=your-regtech-username
REGTECH_PASSWORD=your-regtech-password
SECUDIUM_USERNAME=your-secudium-username
SECUDIUM_PASSWORD=your-secudium-password

# 보안 설정
MAX_AUTH_ATTEMPTS=5
BLOCK_DURATION_HOURS=1
RESTART_PROTECTION=false

# 모니터링 설정
PROMETHEUS_ENABLED=true
HEALTH_DASHBOARD_ENABLED=true
""")
    
    def create_manifest(self):
        """매니페스트 파일 생성"""
        print("\n📋 매니페스트 파일 생성 중...")
        
        # 패키지 크기 계산
        total_size = sum(
            f.stat().st_size for f in self.package_dir.rglob('*') 
            if f.is_file()
        )
        
        self.manifest.update({
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "file_count": len(list(self.package_dir.rglob('*'))),
            "checksum": self._calculate_package_checksum(),
            "installation": {
                "system_requirements": {
                    "os": "Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)",
                    "cpu": "x86_64",
                    "memory": "4GB RAM minimum, 8GB recommended",
                    "disk": "10GB free space minimum",
                    "docker": "20.10+",
                    "python": "3.9+"
                },
                "installation_time": "15-30 minutes",
                "main_script": "scripts/install.sh"
            }
        })
        
        # 매니페스트 저장
        manifest_file = self.package_dir / "package-manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ 매니페스트 저장: {manifest_file}")
    
    def create_archive(self):
        """최종 아카이브 생성"""
        print("\n📦 최종 아카이브 생성 중...")
        
        archive_name = f"{PACKAGE_NAME}-v{VERSION}.tar.gz"
        archive_path = self.output_dir / archive_name
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(self.package_dir, arcname=self.package_dir.name)
        
        # 체크섬 파일 생성
        checksum = self._calculate_file_checksum(archive_path)
        checksum_file = self.output_dir / f"{archive_name}.sha256"
        
        with open(checksum_file, 'w') as f:
            f.write(f"{checksum}  {archive_name}\n")
        
        # 크기 정보
        size_mb = archive_path.stat().st_size / 1024 / 1024
        
        print(f"  ✅ 아카이브 생성됨: {archive_path}")
        print(f"  📏 크기: {size_mb:.2f} MB")
        print(f"  🔒 체크섬: {checksum}")
        
        return archive_path
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """파일 체크섬 계산"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _calculate_package_checksum(self) -> str:
        """패키지 체크섬 계산"""
        all_files = sorted(self.package_dir.rglob('*'))
        hash_sha256 = hashlib.sha256()
        
        for file_path in all_files:
            if file_path.is_file():
                relative_path = file_path.relative_to(self.package_dir)
                hash_sha256.update(str(relative_path).encode())
                
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def build(self):
        """전체 빌드 프로세스 실행"""
        print(f"🚀 {PACKAGE_NAME} v{VERSION} 오프라인 패키지 생성 시작")
        print("=" * 60)
        
        try:
            # 1. 기본 구조 생성
            self.create_directory_structure()
            
            # 2. 전문 매니저들을 통한 컴포넌트 생성
            self.dependency_manager.collect_dependencies(self.manifest)
            self.docker_manager.export_images(self.manifest)
            self.copy_source_code()
            self.script_generator.create_all_scripts(self.manifest)
            self.config_generator.create_all_configs(self.manifest)
            
            # 3. 문서 및 도구 생성
            self._create_documentation()
            self._create_verification_tools()
            
            # 4. 최종화
            self.create_manifest()
            archive_path = self.create_archive()
            
            print("\n🎉 오프라인 패키지 생성 완료!")
            print(f"📦 패키지: {archive_path}")
            print(f"📏 크기: {archive_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            return archive_path
            
        except Exception as e:
            print(f"\n❌ 패키지 생성 실패: {e}")
            raise
    
    def _create_documentation(self):
        """문서 생성 (간단 버전)"""
        docs_dir = self.dirs["docs"]
        
        guide_content = """# 블랙리스트 시스템 설치 가이드

## 시스템 요구사항

- OS: Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
- CPU: x86_64
- 메모리: 4GB RAM 최소, 8GB 권장
- 디스크: 10GB 여유 공간 최소
- Docker: 20.10+
- Python: 3.9+

## 설치 단계

1. 패키지 압축 해제
2. 설치 스크립트 실행: `sudo ./scripts/install.sh`
3. 환경 변수 설정: `/opt/blacklist/.env`
4. 서비스 시작: `systemctl start blacklist`

자세한 내용은 각 스크립트의 주석을 참고하세요.
"""
        
        guide_file = docs_dir / "installation-guide.md"
        with open(guide_file, 'w') as f:
            f.write(guide_content)
        
        self.manifest["components"]["documentation"] = {
            "status": "success",
            "documents": ["installation-guide.md"]
        }
    
    def _create_verification_tools(self):
        """검증 도구 생성 (간단 버전)"""
        tools_dir = self.dirs["tools"]
        
        verify_script = """#!/bin/bash
# 설치 검증 스크립트

echo "🔍 블랙리스트 시스템 설치 검증"
echo "==================================="

# 서비스 상태 확인
if systemctl is-active --quiet blacklist; then
    echo "✅ systemd 서비스: 실행 중"
else
    echo "❌ systemd 서비스: 중지됨"
fi

# API 응답 확인
if curl -s -f "http://localhost:32542/health" >/dev/null; then
    echo "✅ API 엔드포인트: 정상"
else
    echo "❌ API 엔드포인트: 응답 없음"
fi

echo "==================================="
echo "검증 완료"
"""
        
        verify_file = tools_dir / "verify-installation.sh"
        with open(verify_file, 'w') as f:
            f.write(verify_script)
        verify_file.chmod(0o755)
        
        self.manifest["components"]["verification_tools"] = {
            "status": "success",
            "tools": ["verify-installation.sh"]
        }
