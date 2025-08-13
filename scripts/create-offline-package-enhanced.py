#!/usr/bin/env python3
"""
Enhanced Offline Package Builder for Blacklist Management System
완전 자동화된 오프라인 배포 패키지 생성기

Features:
- Docker 이미지 자동 내보내기
- 모든 의존성 패키지 수집
- Kubernetes 매니페스트 포함
- 자동 설치 스크립트 생성
- 검증 도구 포함
"""

import os
import sys
import json
import shutil
import subprocess
import logging
import tarfile
from datetime import datetime
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OfflinePackageBuilder:
    def __init__(self, version="v2.0"):
        self.version = version
        self.project_root = Path(__file__).parent.parent
        self.build_dir = self.project_root / f"offline-build-{version}"
        self.package_name = f"blacklist-offline-package-{version}.tar.gz"
        
        # 필수 파일 리스트
        self.required_files = [
            "README.md",
            "requirements.txt",
            "docker-compose.yml",
            "Dockerfile",
            "chart/",
            "src/",
            "app/",
            "static/",
            "templates/",
            "config/",
            "scripts/",
            "docs/",
        ]
    
    def create_build_directory(self):
        """빌드 디렉토리 생성 및 초기화"""
        logger.info(f"Creating build directory: {self.build_dir}")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        
        self.build_dir.mkdir(parents=True)
        
        # 서브디렉토리 생성
        (self.build_dir / "docker-images").mkdir()
        (self.build_dir / "python-packages").mkdir()
        (self.build_dir / "scripts").mkdir()
        (self.build_dir / "k8s").mkdir()
        (self.build_dir / "docs").mkdir()
    
    def copy_source_files(self):
        """소스 파일 복사"""
        logger.info("Copying source files...")
        
        for file_pattern in self.required_files:
            source_path = self.project_root / file_pattern
            if source_path.exists():
                if source_path.is_dir():
                    shutil.copytree(
                        source_path, 
                        self.build_dir / file_pattern,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache')
                    )
                else:
                    shutil.copy2(source_path, self.build_dir / file_pattern)
                logger.info(f"✅ Copied {file_pattern}")
            else:
                logger.warning(f"⚠️  {file_pattern} not found, skipping")
    
    def export_docker_images(self):
        """Docker 이미지 내보내기"""
        logger.info("Exporting Docker images...")
        
        images = [
            "registry.jclee.me/jclee94/blacklist:latest",
            "redis:7-alpine",
            "postgres:13-alpine"
        ]
        
        docker_dir = self.build_dir / "docker-images"
        
        for image in images:
            try:
                # 이미지 풀
                subprocess.run(["docker", "pull", image], check=True)
                
                # 이미지 이름에서 파일명 생성
                filename = image.replace("/", "_").replace(":", "_") + ".tar"
                output_path = docker_dir / filename
                
                # 이미지 내보내기
                subprocess.run(
                    ["docker", "save", "-o", str(output_path), image], 
                    check=True
                )
                
                logger.info(f"✅ Exported {image} -> {filename}")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Failed to export {image}: {e}")
    
    def collect_python_packages(self):
        """Python 패키지 수집"""
        logger.info("Collecting Python packages...")
        
        packages_dir = self.build_dir / "python-packages"
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            logger.warning("requirements.txt not found")
            return
        
        try:
            # pip download로 모든 의존성 패키지 다운로드
            subprocess.run([
                "pip", "download", 
                "-r", str(requirements_file),
                "-d", str(packages_dir),
                "--no-deps"  # 의존성 포함하지 않음 (별도 처리)
            ], check=True)
            
            # 의존성까지 포함해서 다운로드
            subprocess.run([
                "pip", "download", 
                "-r", str(requirements_file),
                "-d", str(packages_dir)
            ], check=True)
            
            logger.info("✅ Python packages collected")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to collect packages: {e}")
    
    def create_install_script(self):
        """자동 설치 스크립트 생성"""
        logger.info("Creating installation script...")
        
        install_script = self.build_dir / "install-offline.sh"
        
        script_content = '''#!/bin/bash
# Blacklist Management System - 오프라인 자동 설치 스크립트
# 버전: {version}
# 생성일: {date}

set -e  # 에러 발생 시 스크립트 종료

echo "🚀 Blacklist Management System 오프라인 설치 시작..."
echo "버전: {version}"
echo "설치 시작 시간: $(date)"

# 컬러 출력 함수
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

log_info() {{
    echo -e "${{GREEN}}[INFO]${{NC}} $1"
}}

log_warn() {{
    echo -e "${{YELLOW}}[WARN]${{NC}} $1"
}}

log_error() {{
    echo -e "${{RED}}[ERROR]${{NC}} $1"
}}

# 시스템 요구사항 확인
check_requirements() {{
    log_info "시스템 요구사항 확인 중..."
    
    # RAM 확인 (최소 4GB)
    MEMORY_GB=$(free -g | awk '/^Mem:/ {{print $2}}')
    if [ "$MEMORY_GB" -lt 4 ]; then
        log_warn "메모리가 부족합니다. 최소 4GB 필요 (현재: ${{MEMORY_GB}}GB)"
    fi
    
    # 디스크 공간 확인 (최소 10GB)
    DISK_GB=$(df -BG . | awk 'NR==2 {{print $4}}' | sed 's/G//')
    if [ "$DISK_GB" -lt 10 ]; then
        log_error "디스크 공간이 부족합니다. 최소 10GB 필요 (현재: ${{DISK_GB}}GB)"
        exit 1
    fi
    
    log_info "✅ 시스템 요구사항 확인 완료"
}}

# Docker 설치
install_docker() {{
    if command -v docker &> /dev/null; then
        log_info "Docker가 이미 설치되어 있습니다."
        return
    fi
    
    log_info "Docker 설치 중..."
    
    # Docker 설치 (Ubuntu/CentOS 자동 감지)
    if [ -f /etc/ubuntu-release ] || [ -f /etc/debian_version ]; then
        apt-get update
        apt-get install -y docker.io docker-compose
    elif [ -f /etc/redhat-release ]; then
        yum install -y docker docker-compose
    else
        log_error "지원되지 않는 OS입니다."
        exit 1
    fi
    
    # Docker 서비스 시작
    systemctl start docker
    systemctl enable docker
    
    log_info "✅ Docker 설치 완료"
}}

# Docker 이미지 로드
load_docker_images() {{
    log_info "Docker 이미지 로드 중..."
    
    cd docker-images
    for image_file in *.tar; do
        if [ -f "$image_file" ]; then
            log_info "로딩: $image_file"
            docker load -i "$image_file"
        fi
    done
    cd ..
    
    log_info "✅ Docker 이미지 로드 완료"
}}

# Python 패키지 설치
install_python_packages() {{
    log_info "Python 패키지 설치 중..."
    
    cd python-packages
    pip install *.whl *.tar.gz 2>/dev/null || true
    cd ..
    
    log_info "✅ Python 패키지 설치 완료"
}}

# 애플리케이션 배포
deploy_application() {{
    log_info "애플리케이션 배포 중..."
    
    # Docker Compose로 서비스 시작
    docker-compose up -d
    
    # 서비스 시작 대기
    log_info "서비스 시작 대기 중..."
    sleep 30
    
    log_info "✅ 애플리케이션 배포 완료"
}}

# 헬스체크
health_check() {{
    log_info "헬스체크 실행 중..."
    
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s http://localhost:32542/health > /dev/null; then
            log_info "✅ 헬스체크 성공"
            return
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_info "대기 중... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 5
    done
    
    log_error "❌ 헬스체크 실패"
    exit 1
}}

# 설치 완료 정보 출력
print_completion_info() {{
    echo ""
    echo "🎉 설치가 완료되었습니다!"
    echo ""
    echo "📊 접속 정보:"
    echo "  웹 대시보드: http://localhost:32542"
    echo "  API 헬스체크: http://localhost:32542/health"
    echo "  메트릭: http://localhost:32542/metrics"
    echo ""
    echo "🔧 유용한 명령어:"
    echo "  서비스 상태: docker-compose ps"
    echo "  로그 확인: docker-compose logs -f"
    echo "  서비스 중지: docker-compose down"
    echo ""
    echo "📚 추가 도움말: ./verify-installation.sh"
    echo ""
}}

# 메인 설치 프로세스
main() {{
    echo "=============================================="
    echo "   Blacklist Management System"
    echo "   오프라인 자동 설치"
    echo "=============================================="
    
    check_requirements
    install_docker
    load_docker_images
    install_python_packages
    deploy_application
    health_check
    print_completion_info
    
    echo "설치 완료 시간: $(date)"
}}

# 스크립트 실행
main "$@"
'''.format(version=self.version, date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        with open(install_script, 'w') as f:
            f.write(script_content)
        
        # 실행 권한 부여
        install_script.chmod(0o755)
        logger.info("✅ Installation script created")
    
    def create_verification_script(self):
        """검증 스크립트 생성"""
        logger.info("Creating verification script...")
        
        verify_script = self.build_dir / "verify-installation.sh"
        
        script_content = '''#!/bin/bash
# 설치 검증 스크립트

echo "🔍 Blacklist Management System 설치 검증..."

# 서비스 상태 확인
echo "1. Docker 서비스 상태:"
docker-compose ps

echo ""
echo "2. API 헬스체크:"
curl -s http://localhost:32542/health | jq . || echo "jq not found, raw output:"
curl -s http://localhost:32542/health

echo ""
echo "3. 시스템 리소스:"
echo "메모리 사용량:"
free -h

echo ""
echo "디스크 사용량:"
df -h

echo ""
echo "4. 포트 확인:"
netstat -tulpn | grep :32542 || ss -tulpn | grep :32542

echo ""
echo "✅ 검증 완료"
'''
        
        with open(verify_script, 'w') as f:
            f.write(script_content)
        
        verify_script.chmod(0o755)
        logger.info("✅ Verification script created")
    
    def create_package_info(self):
        """패키지 정보 파일 생성"""
        logger.info("Creating package info...")
        
        info = {
            "name": "Blacklist Management System",
            "version": self.version,
            "build_date": datetime.now().isoformat(),
            "description": "Complete offline deployment package",
            "author": "이재철 (JCLEE)",
            "email": "qws941@kakao.com",
            "github": "https://github.com/JCLEE94/blacklist",
            "requirements": {
                "min_memory": "4GB",
                "min_disk": "10GB",
                "min_cpu": "2 cores",
                "os": "Ubuntu 18.04+ / CentOS 7+ / RHEL 7+"
            },
            "services": {
                "main_app": "port 32542",
                "redis": "port 6379",
                "postgres": "port 5432 (optional)"
            },
            "installation_time": "15-30 minutes"
        }
        
        with open(self.build_dir / "package-info.json", 'w') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        
        logger.info("✅ Package info created")
    
    def create_tar_package(self):
        """최종 tar.gz 패키지 생성"""
        logger.info(f"Creating final package: {self.package_name}")
        
        package_path = self.project_root / self.package_name
        
        with tarfile.open(package_path, 'w:gz') as tar:
            tar.add(self.build_dir, arcname=f"blacklist-offline-package-{self.version}")
        
        # 패키지 정보 출력
        package_size = package_path.stat().st_size / (1024**3)  # GB
        logger.info(f"✅ Package created: {package_path}")
        logger.info(f"📦 Package size: {package_size:.2f} GB")
        
        return package_path
    
    def build(self):
        """전체 빌드 프로세스 실행"""
        try:
            logger.info("🚀 Starting offline package build...")
            
            self.create_build_directory()
            self.copy_source_files()
            self.export_docker_images()
            self.collect_python_packages()
            self.create_install_script()
            self.create_verification_script()
            self.create_package_info()
            
            package_path = self.create_tar_package()
            
            # 임시 빌드 디렉토리 정리
            shutil.rmtree(self.build_dir)
            
            logger.info("🎉 Build completed successfully!")
            logger.info(f"📦 Package: {package_path}")
            logger.info("📋 Next steps:")
            logger.info("  1. Transfer package to target server")
            logger.info("  2. Extract: tar -xzf blacklist-offline-package-v2.0.tar.gz")
            logger.info("  3. Install: sudo ./install-offline.sh")
            
            return package_path
            
        except Exception as e:
            logger.error(f"❌ Build failed: {e}")
            raise

def main():
    if len(sys.argv) > 1:
        version = sys.argv[1]
    else:
        version = "v2.0"
    
    builder = OfflinePackageBuilder(version)
    builder.build()

if __name__ == "__main__":
    main()