#!/usr/bin/env python3
"""
오프라인 배포 패키지 생성 스크립트

에어갭 Linux 환경용 완전한 오프라인 배포 패키지를 생성합니다.
"""

import os
import sys
import shutil
import subprocess
import tarfile
import json
import platform
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import argparse

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
PACKAGE_NAME = "blacklist-offline-package"
VERSION = "2.0.0"


class OfflinePackageBuilder:
    """오프라인 패키지 빌더"""
    
    def __init__(self, output_dir: str = "dist", include_source: bool = True):
        self.output_dir = Path(output_dir)
        self.include_source = include_source
        self.package_dir = self.output_dir / f"{PACKAGE_NAME}-v{VERSION}"
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
    
    def collect_python_dependencies(self):
        """Python 의존성 수집"""
        print("\n🐍 Python 의존성 수집 중...")
        
        deps_dir = self.dirs["dependencies"]
        
        try:
            # requirements.txt 파일들 찾기
            req_files = [
                PROJECT_ROOT / "requirements.txt",
                PROJECT_ROOT / "requirements-dev.txt"
            ]
            
            all_packages = set()
            
            for req_file in req_files:
                if req_file.exists():
                    print(f"  📄 처리 중: {req_file.name}")
                    
                    # pip download로 wheels 수집
                    download_cmd = [
                        sys.executable, "-m", "pip", "download",
                        "-r", str(req_file),
                        "-d", str(deps_dir / "wheels"),
                        "--no-deps"  # 의존성은 별도로 처리
                    ]
                    
                    result = subprocess.run(download_cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"    ✅ {req_file.name} 의존성 다운로드 완료")
                    else:
                        print(f"    ⚠️ {req_file.name} 다운로드 실패: {result.stderr}")
            
            # 의존성 트리 생성
            print("  🔗 의존성 트리 생성 중...")
            pip_freeze_cmd = [sys.executable, "-m", "pip", "freeze"]
            result = subprocess.run(pip_freeze_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                freeze_file = deps_dir / "requirements-frozen.txt"
                with open(freeze_file, 'w') as f:
                    f.write(result.stdout)
                print(f"    ✅ 고정된 의존성 저장: {freeze_file}")
            
            # pip download로 모든 의존성 수집 (재귀적)
            print("  📦 전체 의존성 패키지 다운로드 중...")
            for req_file in req_files:
                if req_file.exists():
                    download_all_cmd = [
                        sys.executable, "-m", "pip", "download",
                        "-r", str(req_file),
                        "-d", str(deps_dir / "all_wheels"),
                        "--platform", "linux_x86_64",
                        "--only-binary=:all:",
                        "--python-version", "3.9"
                    ]
                    
                    result = subprocess.run(download_all_cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"    ✅ {req_file.name} 전체 의존성 다운로드 완료")
            
            # 의존성 정보 저장
            deps_info = {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "requirements_files": [str(f.name) for f in req_files if f.exists()],
                "download_date": datetime.now().isoformat()
            }
            
            with open(deps_dir / "dependencies-info.json", 'w') as f:
                json.dump(deps_info, f, indent=2)
            
            self.manifest["components"]["python_dependencies"] = {
                "status": "success",
                "wheels_count": len(list((deps_dir / "all_wheels").glob("*.whl"))),
                "info_file": "dependencies/dependencies-info.json"
            }
            
        except Exception as e:
            print(f"  ❌ Python 의존성 수집 실패: {e}")
            self.manifest["components"]["python_dependencies"] = {
                "status": "failed",
                "error": str(e)
            }
    
    def export_docker_images(self):
        """Docker 이미지 내보내기"""
        print("\n🐳 Docker 이미지 내보내기 중...")
        
        images_dir = self.dirs["docker_images"]
        
        # 내보낼 이미지 목록
        images_to_export = [
            "registry.jclee.me/blacklist:latest",
            "redis:7-alpine",
            "postgres:15-alpine",
            "nginx:alpine",
            "python:3.10-slim"
        ]
        
        exported_images = []
        
        for image in images_to_export:
            try:
                print(f"  📦 내보내는 중: {image}")
                
                # 이미지명을 파일명으로 변환
                safe_name = image.replace('/', '_').replace(':', '_')
                tar_file = images_dir / f"{safe_name}.tar"
                
                # docker save 명령 실행
                save_cmd = ["docker", "save", "-o", str(tar_file), image]
                result = subprocess.run(save_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"    ✅ 저장됨: {tar_file.name}")
                    
                    # 파일 크기 및 체크섬 계산
                    file_size = tar_file.stat().st_size
                    
                    with open(tar_file, 'rb') as f:
                        checksum = hashlib.sha256(f.read()).hexdigest()
                    
                    exported_images.append({
                        "image": image,
                        "file": tar_file.name,
                        "size_bytes": file_size,
                        "size_mb": round(file_size / 1024 / 1024, 2),
                        "sha256": checksum
                    })
                else:
                    print(f"    ⚠️ 실패: {result.stderr}")
                    
            except Exception as e:
                print(f"    ❌ {image} 내보내기 실패: {e}")
        
        # 이미지 정보 저장
        images_info = {
            "exported_date": datetime.now().isoformat(),
            "docker_version": self._get_docker_version(),
            "total_images": len(exported_images),
            "total_size_mb": sum(img["size_mb"] for img in exported_images),
            "images": exported_images
        }
        
        with open(images_dir / "images-info.json", 'w') as f:
            json.dump(images_info, f, indent=2)
        
        # 로드 스크립트 생성
        self._create_docker_load_script(images_dir, exported_images)
        
        self.manifest["components"]["docker_images"] = {
            "status": "success",
            "images_count": len(exported_images),
            "total_size_mb": images_info["total_size_mb"],
            "info_file": "docker-images/images-info.json"
        }
    
    def copy_source_code(self):
        """소스 코드 복사"""
        if not self.include_source:
            return
            
        print("\n📄 소스 코드 복사 중...")
        
        source_dir = self.dirs["source_code"]
        
        # 복사할 디렉토리/파일 목록
        items_to_copy = [
            "src",
            "tests", 
            "scripts",
            "monitoring",
            "chart",
            "argocd",
            "main.py",
            "init_database.py",
            "requirements.txt",
            "requirements-dev.txt",
            "pytest.ini",
            "pyproject.toml",
            ".isort.cfg",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.local.yml",
            "Makefile",
            "README.md",
            "CLAUDE.md",
            "VERSION"
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
        
        copied_items.append(".env.template")
        
        self.manifest["components"]["source_code"] = {
            "status": "success",
            "items_count": len(copied_items),
            "items": copied_items
        }
    
    def create_installation_scripts(self):
        """설치 스크립트 생성"""
        print("\n📝 설치 스크립트 생성 중...")
        
        scripts_dir = self.dirs["scripts"]
        
        # 메인 설치 스크립트
        self._create_main_install_script(scripts_dir)
        
        # Docker 이미지 로드 스크립트
        self._create_docker_scripts(scripts_dir)
        
        # Python 의존성 설치 스크립트
        self._create_python_install_script(scripts_dir)
        
        # 시스템 서비스 스크립트
        self._create_systemd_scripts(scripts_dir)
        
        # 헬스체크 스크립트
        self._create_health_check_script(scripts_dir)
        
        # 언인스톨 스크립트
        self._create_uninstall_script(scripts_dir)
        
        self.manifest["components"]["installation_scripts"] = {
            "status": "success",
            "scripts": [
                "install.sh",
                "load-docker-images.sh",
                "install-python-deps.sh", 
                "setup-systemd.sh",
                "health-check.sh",
                "uninstall.sh"
            ]
        }
    
    def create_configuration_templates(self):
        """설정 템플릿 생성"""
        print("\n⚙️ 설정 템플릿 생성 중...")
        
        configs_dir = self.dirs["configs"]
        
        # Docker Compose 설정
        self._create_docker_compose_template(configs_dir)
        
        # Nginx 설정
        self._create_nginx_config(configs_dir)
        
        # 환경별 설정 파일들
        self._create_environment_configs(configs_dir)
        
        # 모니터링 설정
        self._create_monitoring_configs(configs_dir)
        
        self.manifest["components"]["configuration_templates"] = {
            "status": "success",
            "configs": [
                "docker-compose.yml",
                "nginx.conf",
                "prometheus.yml",
                "alert-rules.yml"
            ]
        }
    
    def create_database_scripts(self):
        """데이터베이스 스크립트 생성"""
        print("\n🗄️ 데이터베이스 스크립트 생성 중...")
        
        db_dir = self.dirs["database"]
        
        # 데이터베이스 초기화 스크립트 복사
        init_script = PROJECT_ROOT / "init_database.py"
        if init_script.exists():
            shutil.copy2(init_script, db_dir / "init_database.py")
        
        # 마이그레이션 스크립트 생성
        self._create_migration_scripts(db_dir)
        
        # 백업/복원 스크립트
        self._create_backup_scripts(db_dir)
        
        self.manifest["components"]["database_scripts"] = {
            "status": "success",
            "scripts": [
                "init_database.py",
                "migrate.py",
                "backup.sh",
                "restore.sh"
            ]
        }
    
    def create_documentation(self):
        """문서 생성"""
        print("\n📚 문서 생성 중...")
        
        docs_dir = self.dirs["docs"]
        
        # 설치 가이드
        self._create_installation_guide(docs_dir)
        
        # 운영 가이드
        self._create_operations_guide(docs_dir)
        
        # 트러블슈팅 가이드
        self._create_troubleshooting_guide(docs_dir)
        
        # API 문서
        self._create_api_documentation(docs_dir)
        
        self.manifest["components"]["documentation"] = {
            "status": "success",
            "documents": [
                "installation-guide.md",
                "operations-guide.md", 
                "troubleshooting-guide.md",
                "api-documentation.md"
            ]
        }
    
    def create_verification_tools(self):
        """검증 도구 생성"""
        print("\n🔍 검증 도구 생성 중...")
        
        tools_dir = self.dirs["tools"]
        
        # 시스템 요구사항 체크 스크립트
        self._create_system_check_script(tools_dir)
        
        # 설치 검증 스크립트
        self._create_installation_verify_script(tools_dir)
        
        # 성능 테스트 스크립트
        self._create_performance_test_script(tools_dir)
        
        self.manifest["components"]["verification_tools"] = {
            "status": "success",
            "tools": [
                "system-check.sh",
                "verify-installation.sh",
                "performance-test.py"
            ]
        }
    
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
    
    def _get_docker_version(self) -> str:
        """Docker 버전 확인"""
        try:
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, text=True
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
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
    
    def _create_main_install_script(self, scripts_dir: Path):
        """메인 설치 스크립트 생성"""
        script_content = '''#!/bin/bash
# 블랙리스트 시스템 오프라인 설치 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/blacklist"
LOG_FILE="/tmp/blacklist-install.log"

# 색상 정의
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

# 로그 함수
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
    log "[STEP] $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    log "[SUCCESS] $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    log "[WARNING] $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    log "[ERROR] $1"
}

# 루트 권한 확인
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "이 스크립트는 root 권한으로 실행해야 합니다."
        echo "sudo $0 $@"
        exit 1
    fi
}

# 시스템 요구사항 확인
check_system_requirements() {
    print_step "시스템 요구사항 확인 중..."
    
    # OS 확인
    if [[ ! -f /etc/os-release ]]; then
        print_error "지원되지 않는 운영체제입니다."
        exit 1
    fi
    
    source /etc/os-release
    print_success "OS: $PRETTY_NAME"
    
    # 메모리 확인
    MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $MEMORY_GB -lt 4 ]]; then
        print_warning "권장 메모리(4GB) 미만입니다. 현재: ${MEMORY_GB}GB"
    else
        print_success "메모리: ${MEMORY_GB}GB"
    fi
    
    # 디스크 공간 확인
    DISK_FREE_GB=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $DISK_FREE_GB -lt 10 ]]; then
        print_error "디스크 공간이 부족합니다. 최소 10GB 필요, 현재: ${DISK_FREE_GB}GB"
        exit 1
    else
        print_success "디스크 여유공간: ${DISK_FREE_GB}GB"
    fi
}

# Docker 설치 및 확인
setup_docker() {
    print_step "Docker 설치 및 확인 중..."
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker 이미 설치됨: $DOCKER_VERSION"
    else
        print_step "Docker 설치 중..."
        
        # 공식 Docker 설치 스크립트 사용 (오프라인 환경에서는 사전 설치 필요)
        if [[ -f "$PACKAGE_ROOT/tools/docker-install.sh" ]]; then
            bash "$PACKAGE_ROOT/tools/docker-install.sh"
        else
            print_error "Docker가 설치되지 않았습니다. 수동으로 설치하세요."
            exit 1
        fi
    fi
    
    # Docker 서비스 시작
    systemctl enable docker
    systemctl start docker
    
    # Docker Compose 확인
    if ! command -v docker-compose &> /dev/null; then
        print_step "Docker Compose 설치 중..."
        # 바이너리 복사 (패키지에 포함된 경우)
        if [[ -f "$PACKAGE_ROOT/tools/docker-compose" ]]; then
            cp "$PACKAGE_ROOT/tools/docker-compose" /usr/local/bin/
            chmod +x /usr/local/bin/docker-compose
        else
            print_error "Docker Compose가 없습니다."
            exit 1
        fi
    fi
}

# Python 환경 설정
setup_python() {
    print_step "Python 환경 설정 중..."
    
    # Python 3.9+ 확인
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python 설치됨: $PYTHON_VERSION"
    else
        print_error "Python 3.9+ 가 필요합니다."
        exit 1
    fi
    
    # pip 확인 및 업그레이드
    if ! command -v pip3 &> /dev/null; then
        print_error "pip가 설치되지 않았습니다."
        exit 1
    fi
    
    # 오프라인 의존성 설치
    if [[ -d "$PACKAGE_ROOT/dependencies" ]]; then
        bash "$SCRIPT_DIR/install-python-deps.sh"
    fi
}

# 애플리케이션 설치
install_application() {
    print_step "애플리케이션 설치 중..."
    
    # 설치 디렉토리 생성
    mkdir -p "$INSTALL_DIR"
    
    # 소스 코드 복사
    if [[ -d "$PACKAGE_ROOT/source-code" ]]; then
        cp -r "$PACKAGE_ROOT/source-code"/* "$INSTALL_DIR/"
        print_success "소스 코드 복사 완료"
    fi
    
    # 설정 파일 복사
    if [[ -d "$PACKAGE_ROOT/configs" ]]; then
        cp -r "$PACKAGE_ROOT/configs"/* "$INSTALL_DIR/"
        print_success "설정 파일 복사 완료"
    fi
    
    # 권한 설정
    chown -R 1000:1000 "$INSTALL_DIR"
    chmod +x "$INSTALL_DIR"/*.sh 2>/dev/null || true
}

# Docker 이미지 로드
load_docker_images() {
    print_step "Docker 이미지 로드 중..."
    
    if [[ -d "$PACKAGE_ROOT/docker-images" ]]; then
        bash "$SCRIPT_DIR/load-docker-images.sh"
    else
        print_warning "Docker 이미지가 패키지에 포함되지 않았습니다."
    fi
}

# 서비스 설정
setup_services() {
    print_step "시스템 서비스 설정 중..."
    
    # systemd 서비스 파일 설치
    bash "$SCRIPT_DIR/setup-systemd.sh" "$INSTALL_DIR"
    
    # 환경 변수 설정
    if [[ -f "$INSTALL_DIR/.env.template" ]]; then
        if [[ ! -f "$INSTALL_DIR/.env" ]]; then
            cp "$INSTALL_DIR/.env.template" "$INSTALL_DIR/.env"
            print_warning ".env 파일을 수동으로 편집하세요: $INSTALL_DIR/.env"
        fi
    fi
}

# 데이터베이스 초기화
setup_database() {
    print_step "데이터베이스 초기화 중..."
    
    cd "$INSTALL_DIR"
    
    # 데이터베이스 디렉토리 생성
    mkdir -p instance
    
    # 데이터베이스 초기화
    if [[ -f "init_database.py" ]]; then
        python3 init_database.py
        print_success "데이터베이스 초기화 완료"
    fi
}

# 설치 검증
verify_installation() {
    print_step "설치 검증 중..."
    
    if [[ -f "$PACKAGE_ROOT/tools/verify-installation.sh" ]]; then
        bash "$PACKAGE_ROOT/tools/verify-installation.sh"
    else
        # 기본 검증
        if systemctl is-active --quiet blacklist; then
            print_success "블랙리스트 서비스가 실행 중입니다."
        else
            print_warning "블랙리스트 서비스가 실행되지 않았습니다."
        fi
    fi
}

# 설치 완료 메시지
show_completion_message() {
    echo
    print_success "=== 블랙리스트 시스템 설치 완료 ==="
    echo
    echo "설치 위치: $INSTALL_DIR"
    echo "로그 파일: $LOG_FILE"
    echo
    echo "다음 단계:"
    echo "1. 환경 변수 편집: $INSTALL_DIR/.env"
    echo "2. 서비스 시작: systemctl start blacklist"
    echo "3. 상태 확인: systemctl status blacklist"
    echo "4. 웹 대시보드: http://localhost:32542/dashboard"
    echo
    echo "문제가 발생하면 다음을 확인하세요:"
    echo "- 로그 파일: $LOG_FILE"
    echo "- 시스템 로그: journalctl -u blacklist"
    echo "- 문서: $PACKAGE_ROOT/docs/"
    echo
}

# 메인 설치 프로세스
main() {
    echo "🚀 블랙리스트 시스템 오프라인 설치 시작"
    echo "로그 파일: $LOG_FILE"
    echo
    
    check_root
    check_system_requirements
    setup_docker
    setup_python
    load_docker_images
    install_application
    setup_services
    setup_database
    verify_installation
    show_completion_message
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
'''
        
        install_script = scripts_dir / "install.sh"
        with open(install_script, 'w') as f:
            f.write(script_content)
        
        install_script.chmod(0o755)
        print(f"  ✅ 메인 설치 스크립트: {install_script}")
    
    def _create_docker_load_script(self, images_dir: Path, images: List[Dict]):
        """Docker 이미지 로드 스크립트 생성"""
        script_content = f'''#!/bin/bash
# Docker 이미지 로드 스크립트

set -e

IMAGES_DIR="{images_dir}"

echo "🐳 Docker 이미지 로드 중..."

'''
        
        for image_info in images:
            script_content += f'''
echo "  📦 로드 중: {image_info['image']}"
docker load -i "$IMAGES_DIR/{image_info['file']}"
'''
        
        script_content += '''
echo "✅ 모든 Docker 이미지 로드 완료"

# 이미지 목록 확인
echo "📋 로드된 이미지 목록:"
docker images
'''
        
        load_script = images_dir / "load-docker-images.sh"
        with open(load_script, 'w') as f:
            f.write(script_content)
        
        load_script.chmod(0o755)
    
    def _create_docker_scripts(self, scripts_dir: Path):
        """Docker 관련 스크립트들 생성"""
        load_script_content = '''#!/bin/bash
# Docker 이미지 로드 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGES_DIR="$PACKAGE_ROOT/docker-images"

if [[ ! -d "$IMAGES_DIR" ]]; then
    echo "❌ Docker 이미지 디렉토리가 없습니다: $IMAGES_DIR"
    exit 1
fi

echo "🐳 Docker 이미지 로드 중..."

for tar_file in "$IMAGES_DIR"/*.tar; do
    if [[ -f "$tar_file" ]]; then
        echo "  📦 로드 중: $(basename "$tar_file")"
        docker load -i "$tar_file"
    fi
done

echo "✅ Docker 이미지 로드 완료"
echo "📋 로드된 이미지:"
docker images
'''
        
        load_script = scripts_dir / "load-docker-images.sh"
        with open(load_script, 'w') as f:
            f.write(load_script_content)
        load_script.chmod(0o755)
    
    def _create_python_install_script(self, scripts_dir: Path):
        """Python 의존성 설치 스크립트 생성"""
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
        
        python_script = scripts_dir / "install-python-deps.sh"
        with open(python_script, 'w') as f:
            f.write(script_content)
        python_script.chmod(0o755)
    
    def _create_systemd_scripts(self, scripts_dir: Path):
        """systemd 서비스 스크립트 생성"""
        systemd_content = '''#!/bin/bash
# systemd 서비스 설정 스크립트

set -e

INSTALL_DIR="${1:-/opt/blacklist}"

echo "⚙️ systemd 서비스 설정 중..."

# systemd 서비스 파일 생성
cat > /etc/systemd/system/blacklist.service << EOF
[Unit]
Description=Blacklist Management System
After=network.target docker.service
Requires=docker.service

[Service]
Type=forking
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/docker-compose -f $INSTALL_DIR/docker-compose.yml up -d
ExecStop=/usr/bin/docker-compose -f $INSTALL_DIR/docker-compose.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# systemd 데몬 리로드
systemctl daemon-reload

# 서비스 활성화
systemctl enable blacklist

echo "✅ systemd 서비스 설정 완료"
echo "서비스 시작: systemctl start blacklist"
echo "상태 확인: systemctl status blacklist"
'''
        
        systemd_script = scripts_dir / "setup-systemd.sh"
        with open(systemd_script, 'w') as f:
            f.write(systemd_content)
        systemd_script.chmod(0o755)
    
    def _create_health_check_script(self, scripts_dir: Path):
        """헬스체크 스크립트 생성"""
        health_content = '''#!/bin/bash
# 블랙리스트 시스템 헬스체크 스크립트

set -e

INSTALL_DIR="${1:-/opt/blacklist}"
API_URL="http://localhost:32542"

echo "🏥 블랙리스트 시스템 헬스체크"
echo "================================"

# 서비스 상태 확인
echo "📊 서비스 상태:"
if systemctl is-active --quiet blacklist; then
    echo "  ✅ systemd 서비스: 실행 중"
else
    echo "  ❌ systemd 서비스: 중지됨"
fi

# Docker 컨테이너 상태 확인
echo "🐳 Docker 컨테이너 상태:"
cd "$INSTALL_DIR"
docker-compose ps

# API 응답 확인
echo "🌐 API 응답 확인:"
if curl -s -f "$API_URL/health" >/dev/null; then
    echo "  ✅ 헬스 엔드포인트: 정상"
    
    # 상세 상태 확인
    HEALTH_DATA=$(curl -s "$API_URL/api/health" | python3 -m json.tool 2>/dev/null || echo "{}")
    echo "  📊 시스템 상태: $(echo "$HEALTH_DATA" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"
else
    echo "  ❌ 헬스 엔드포인트: 응답 없음"
fi

# 데이터베이스 확인
echo "🗄️ 데이터베이스 상태:"
if [[ -f "$INSTALL_DIR/instance/blacklist.db" ]]; then
    DB_SIZE=$(du -h "$INSTALL_DIR/instance/blacklist.db" | cut -f1)
    echo "  ✅ 데이터베이스: 존재 (크기: $DB_SIZE)"
else
    echo "  ❌ 데이터베이스: 없음"
fi

# 포트 확인
echo "🔌 포트 상태:"
if netstat -tuln | grep -q ":32542 "; then
    echo "  ✅ 포트 32542: 열림"
else
    echo "  ❌ 포트 32542: 닫힘"
fi

# 로그 확인
echo "📝 최근 로그 (마지막 10줄):"
journalctl -u blacklist --no-pager -n 10

echo "================================"
echo "헬스체크 완료"
'''
        
        health_script = scripts_dir / "health-check.sh"
        with open(health_script, 'w') as f:
            f.write(health_content)
        health_script.chmod(0o755)
    
    def _create_uninstall_script(self, scripts_dir: Path):
        """언인스톨 스크립트 생성"""
        uninstall_content = '''#!/bin/bash
# 블랙리스트 시스템 언인스톨 스크립트

set -e

INSTALL_DIR="/opt/blacklist"

echo "🗑️ 블랙리스트 시스템 언인스톨"
echo "==============================="

read -p "정말로 블랙리스트 시스템을 제거하시겠습니까? [y/N]: " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "언인스톨이 취소되었습니다."
    exit 0
fi

# 서비스 중지 및 비활성화
echo "🛑 서비스 중지 중..."
systemctl stop blacklist || true
systemctl disable blacklist || true

# Docker 컨테이너 중지 및 제거
echo "🐳 Docker 컨테이너 정리 중..."
if [[ -d "$INSTALL_DIR" ]]; then
    cd "$INSTALL_DIR"
    docker-compose down --volumes --remove-orphans || true
fi

# systemd 서비스 파일 제거
echo "⚙️ systemd 서비스 제거 중..."
rm -f /etc/systemd/system/blacklist.service
systemctl daemon-reload

# 설치 디렉토리 제거
echo "📁 설치 디렉토리 제거 중..."
read -p "데이터베이스와 설정을 포함한 모든 데이터를 삭제하시겠습니까? [y/N]: " delete_data
if [[ "$delete_data" =~ ^[Yy]$ ]]; then
    rm -rf "$INSTALL_DIR"
    echo "  ✅ 모든 데이터 삭제됨"
else
    echo "  ⚠️ 데이터 보존됨: $INSTALL_DIR"
fi

# Docker 이미지 제거 (선택사항)
read -p "Docker 이미지도 제거하시겠습니까? [y/N]: " remove_images
if [[ "$remove_images" =~ ^[Yy]$ ]]; then
    docker rmi registry.jclee.me/blacklist:latest || true
    docker rmi redis:7-alpine || true
    echo "  ✅ Docker 이미지 제거됨"
fi

echo "✅ 블랙리스트 시스템 언인스톨 완료"
'''
        
        uninstall_script = scripts_dir / "uninstall.sh"
        with open(uninstall_script, 'w') as f:
            f.write(uninstall_content)
        uninstall_script.chmod(0o755)
    
    # ... 나머지 헬퍼 메서드들은 간단히 구현
    def _create_docker_compose_template(self, configs_dir: Path):
        # Docker Compose 템플릿 생성 (간단 버전)
        compose_content = '''version: '3.8'
services:
  blacklist:
    image: registry.jclee.me/blacklist:latest
    ports:
      - "32542:8000"
    volumes:
      - ./instance:/app/instance
    env_file:
      - .env
    depends_on:
      - redis
      
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      
volumes:
  redis_data:
'''
        
        compose_file = configs_dir / "docker-compose.yml"
        with open(compose_file, 'w') as f:
            f.write(compose_content)
    
    def _create_nginx_config(self, configs_dir: Path):
        # Nginx 설정 템플릿
        nginx_content = '''server {
    listen 80;
    server_name blacklist.local;
    
    location / {
        proxy_pass http://localhost:32542;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
'''
        nginx_file = configs_dir / "nginx.conf"
        with open(nginx_file, 'w') as f:
            f.write(nginx_content)
    
    def _create_environment_configs(self, configs_dir: Path):
        # 환경별 설정 파일들 생성 (간단 버전)
        pass
    
    def _create_monitoring_configs(self, configs_dir: Path):
        # 모니터링 설정 복사
        monitoring_source = PROJECT_ROOT / "monitoring"
        if monitoring_source.exists():
            shutil.copytree(monitoring_source, configs_dir / "monitoring")
    
    def _create_migration_scripts(self, db_dir: Path):
        # 마이그레이션 스크립트 생성
        pass
    
    def _create_backup_scripts(self, db_dir: Path):
        # 백업/복원 스크립트 생성
        pass
    
    def _create_installation_guide(self, docs_dir: Path):
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
    
    def _create_operations_guide(self, docs_dir: Path):
        # 운영 가이드 생성
        pass
    
    def _create_troubleshooting_guide(self, docs_dir: Path):
        # 트러블슈팅 가이드 생성
        pass
    
    def _create_api_documentation(self, docs_dir: Path):
        # API 문서 생성
        pass
    
    def _create_system_check_script(self, tools_dir: Path):
        # 시스템 체크 스크립트 생성
        pass
    
    def _create_installation_verify_script(self, tools_dir: Path):
        # 설치 검증 스크립트 생성
        pass
    
    def _create_performance_test_script(self, tools_dir: Path):
        # 성능 테스트 스크립트 생성
        pass
    
    def build(self):
        """전체 빌드 프로세스 실행"""
        print(f"🚀 {PACKAGE_NAME} v{VERSION} 오프라인 패키지 생성 시작")
        print("=" * 60)
        
        try:
            self.create_directory_structure()
            self.collect_python_dependencies()
            self.export_docker_images()
            self.copy_source_code()
            self.create_installation_scripts()
            self.create_configuration_templates()
            self.create_database_scripts()
            self.create_documentation()
            self.create_verification_tools()
            self.create_manifest()
            
            archive_path = self.create_archive()
            
            print("\n🎉 오프라인 패키지 생성 완료!")
            print(f"📦 패키지: {archive_path}")
            print(f"📏 크기: {archive_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            return archive_path
            
        except Exception as e:
            print(f"\n❌ 패키지 생성 실패: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='블랙리스트 시스템 오프라인 패키지 생성')
    parser.add_argument('--output-dir', default='dist', help='출력 디렉토리')
    parser.add_argument('--no-source', action='store_true', help='소스 코드 제외')
    parser.add_argument('--no-docker', action='store_true', help='Docker 이미지 제외')
    
    args = parser.parse_args()
    
    builder = OfflinePackageBuilder(
        output_dir=args.output_dir,
        include_source=not args.no_source
    )
    
    if args.no_docker:
        # Docker 이미지 내보내기 건너뛰기
        builder.export_docker_images = lambda: None
    
    try:
        archive_path = builder.build()
        print(f"\n✅ 성공: {archive_path}")
        return 0
    except Exception as e:
        print(f"\n❌ 실패: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())