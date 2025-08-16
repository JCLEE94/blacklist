#!/usr/bin/env python3
"""
오프라인 배포 패키지 생성 스크립트
에어갭 환경용 완전 자체 포함 패키지 생성
"""

import os
import sys
import shutil
import tarfile
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

def run_command(cmd, check=True):
    """명령어 실행"""
    print(f"🔧 실행: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ 명령어 실패: {result.stderr}")
        sys.exit(1)
    return result

def create_offline_package():
    """오프라인 패키지 생성"""
    print("📦 Blacklist 오프라인 배포 패키지 생성 시작")
    
    # 버전 정보
    try:
        with open('src/config/settings.py', 'r') as f:
            content = f.read()
            version = content.split('app_version = "')[1].split('"')[0]
    except:
        version = "unknown"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"blacklist-offline-{version}-{timestamp}"
    
    print(f"📋 패키지명: {package_name}")
    
    # 임시 디렉토리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir) / package_name
        package_dir.mkdir()
        
        print("📁 필수 파일 복사 중...")
        
        # 애플리케이션 소스 복사
        shutil.copytree('.', package_dir / 'app', 
                       ignore=shutil.ignore_patterns(
                           '.git*', '__pycache__', '*.pyc', 'node_modules',
                           '.pytest_cache', 'htmlcov', '.coverage*',
                           'temp', '*.log', '.env.local'
                       ))
        
        # Docker 관련 파일
        for file in ['Dockerfile', 'docker-compose.yml', 'requirements.txt']:
            if os.path.exists(file):
                shutil.copy(file, package_dir / 'app')
        
        # 설치 스크립트 생성
        install_script = package_dir / 'install-offline.sh'
        install_script.write_text(f'''#!/bin/bash
# Blacklist 오프라인 설치 스크립트 v{version}

set -e

echo "🚀 Blacklist 오프라인 설치 시작"

# Docker 확인
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되지 않았습니다."
    exit 1
fi

# 애플리케이션 디렉토리로 이동
cd app

# 환경 변수 파일 생성
if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "⚙️ .env 파일이 생성되었습니다. 설정을 수정하세요."
fi

# Docker 이미지 빌드
echo "🐳 Docker 이미지 빌드 중..."
docker build -t blacklist:offline .

# 데이터베이스 초기화
echo "🗄️ 데이터베이스 초기화..."
python3 init_database.py

# 디렉토리 생성
mkdir -p data/regtech data/secudium instance logs

# 컨테이너 실행
echo "▶️ 애플리케이션 시작..."
docker run -d \\
    --name blacklist-offline \\
    -p 2542:2542 \\
    -v $(pwd)/instance:/app/instance \\
    -v $(pwd)/data:/app/data \\
    -v $(pwd)/logs:/app/logs \\
    --env-file .env \\
    blacklist:offline

echo "✅ 설치 완료!"
echo "🌐 접속: http://localhost:2542"
echo "🔍 상태 확인: docker logs blacklist-offline"
''')
        install_script.chmod(0o755)
        
        # 검증 스크립트 생성
        verify_script = package_dir / 'verify-installation.sh'
        verify_script.write_text('''#!/bin/bash
# 설치 검증 스크립트

echo "🔍 Blacklist 설치 상태 확인"

# 컨테이너 상태 확인
if docker ps | grep -q blacklist-offline; then
    echo "✅ 컨테이너 실행 중"
else
    echo "❌ 컨테이너가 실행되지 않음"
    exit 1
fi

# 헬스체크
if curl -f http://localhost:2542/health > /dev/null 2>&1; then
    echo "✅ 애플리케이션 정상 응답"
else
    echo "❌ 애플리케이션 응답 없음"
    exit 1
fi

echo "🎉 설치가 정상적으로 완료되었습니다!"
''')
        verify_script.chmod(0o755)
        
        # README 생성
        readme = package_dir / 'README-OFFLINE.md'
        readme.write_text(f'''# Blacklist 오프라인 배포 패키지 v{version}

## 설치 방법

1. 이 패키지를 대상 시스템에 복사
2. `tar -xzf {package_name}.tar.gz`
3. `cd {package_name}`
4. `./install-offline.sh`

## 요구사항

- Docker 20.10+
- Python 3.9+
- 2GB 이상 여유 공간

## 검증

- `./verify-installation.sh` 실행

## 접속

- URL: http://localhost:2542
- 관리자: admin / (auto-generated)

## 지원

- 문서: docs/
- 로그: `docker logs blacklist-offline`
''')
        
        print("📦 패키지 압축 중...")
        
        # 패키지 생성
        output_file = f"{package_name}.tar.gz"
        with tarfile.open(output_file, "w:gz") as tar:
            tar.add(package_dir, arcname=package_name)
        
        # 파일 크기 확인
        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        
        print(f"✅ 오프라인 패키지 생성 완료!")
        print(f"📦 파일: {output_file}")
        print(f"📏 크기: {size_mb:.1f} MB")
        print(f"🔧 설치: tar -xzf {output_file} && cd {package_name} && ./install-offline.sh")

if __name__ == "__main__":
    create_offline_package()