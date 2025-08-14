#!/usr/bin/env python3
"""
오프라인 배포 패키지 생성 스크립트 (완전 리팩토링됨)

에어갭 Linux 환경용 완전한 오프라인 배포 패키지를 생성합니다.
간소화되고 모듈화된 구조로 재작성되었습니다.
"""

import sys
import shutil
import json
import argparse
import tarfile
from pathlib import Path
from datetime import datetime

# 모듈화된 컴포넌트 import
try:
    from offline_package import OfflinePackageBase, DependencyManager, DockerManager
except ImportError:
    print("❌ 모듈화된 패키지 컴포넌트를 찾을 수 없습니다.")
    sys.exit(1)


class OfflinePackageBuilder(
        OfflinePackageBase,
        DependencyManager,
        DockerManager):
    """오프라인 패키지 빌더 - 완전 리팩토링된 메인 클래스"""

    def __init__(self, output_dir: str = "dist", include_source: bool = True):
        super().__init__(output_dir, include_source)

    def build_package(self):
        """패키지 빌드 메인 프로세스"""
        print(f"🚀 Starting offline package build v{self.version}...")

        try:
            # 1. 환경 검증
            if not self.validate_environment():
                print("❌ Environment validation failed")
                return False

            # 2. 디렉토리 설정
            self.setup_directories()

            # 3. 컴포넌트 수집 (병렬 가능)
            self._collect_all_components()

            # 4. 설치 스크립트 생성
            self._create_installation_scripts()

            # 5. 매니페스트 저장
            self._save_manifest()

            # 6. 최종 패키지 생성
            return self._create_final_package()

        except Exception as e:
            print(f"❌ Package build failed: {e}")
            return False

    def _collect_all_components(self):
        """모든 컴포넌트 수집"""
        print("\n📦 Collecting all components...")

        # Python 의존성 (DependencyManager에서)
        self.collect_python_dependencies()

        # 시스템 의존성
        self.collect_system_dependencies()

        # Docker 이미지 (DockerManager에서)
        self.collect_docker_images()

        # 소스 코드
        if self.include_source:
            self._copy_source_code()

        # 문서 및 설정
        self._copy_configs_and_docs()

    def _copy_source_code(self):
        """소스 코드 복사"""
        self.log_progress("Copying source code...")

        # 주요 소스 디렉토리들
        source_dirs = ['src', 'app', 'scripts', 'tests']
        source_files = [
            'main.py',
            'docker-compose.yml',
            'Dockerfile',
            'README.md']

        for dir_name in source_dirs:
            src_dir = self.project_root / dir_name
            if src_dir.exists():
                dest_dir = self.dirs["source_code"] / dir_name
                shutil.copytree(
                    src_dir, dest_dir, ignore=shutil.ignore_patterns(
                        '__pycache__', '*.pyc'))
                print(f"   ✓ Copied {dir_name}/")

        for file_name in source_files:
            src_file = self.project_root / file_name
            if src_file.exists():
                shutil.copy2(src_file, self.dirs["source_code"])
                print(f"   ✓ Copied {file_name}")

        self.log_progress("Source code copied", "source_code")

    def _copy_configs_and_docs(self):
        """설정 및 문서 복사"""
        self.log_progress("Copying configs and documentation...")

        # 설정 파일들
        config_files = ['config', 'chart', 'k8s']
        for config_name in config_files:
            config_path = self.project_root / config_name
            if config_path.exists():
                dest_path = self.dirs["configs"] / config_name
                if config_path.is_file():
                    shutil.copy2(config_path, self.dirs["configs"])
                else:
                    shutil.copytree(config_path, dest_path)
                print(f"   ✓ Copied {config_name}")

        self.log_progress("Configs and docs copied", "configs")

    def _create_installation_scripts(self):
        """설치 스크립트 생성"""
        self.log_progress("Creating installation scripts...")

        # 메인 설치 스크립트
        install_script = self._generate_install_script()
        install_file = self.dirs["scripts"] / "install-offline.sh"

        with open(install_file, 'w') as f:
            f.write(install_script)
        install_file.chmod(0o755)

        # 검증 스크립트
        verify_script = self._generate_verify_script()
        verify_file = self.dirs["scripts"] / "verify-installation.sh"

        with open(verify_file, 'w') as f:
            f.write(verify_script)
        verify_file.chmod(0o755)

        print(f"   ✓ Installation scripts created")
        self.log_progress("Installation scripts created", "install_scripts")

    def _generate_install_script(self) -> str:
        """설치 스크립트 생성"""
        return '''#!/bin/bash
# Blacklist Offline Installation Script v2.0
# Auto-generated installation script

set -e

echo "🚀 Starting Blacklist offline installation..."

# System dependencies
echo "📦 Installing system dependencies..."
if [ -f "dependencies/apt/required_packages.txt" ]; then
    sudo apt update
    sudo apt install -y $(cat dependencies/apt/required_packages.txt | grep -v "^#")
fi

# Python dependencies
echo "🐍 Installing Python dependencies..."
if [ -d "dependencies/pip" ]; then
    pip3 install --no-index --find-links dependencies/pip -r configs/requirements.txt
fi

# Docker images
echo "🐳 Loading Docker images..."
if [ -f "scripts/load-docker-images.sh" ]; then
    bash scripts/load-docker-images.sh
fi

# Source code deployment
echo "📁 Deploying source code..."
if [ -d "source-code" ]; then
    sudo mkdir -p /opt/blacklist
    sudo cp -r source-code/* /opt/blacklist/
    sudo chown -R $USER:$USER /opt/blacklist
fi

echo "✅ Installation completed!"
echo "Run './verify-installation.sh' to validate the installation."
'''

    def _generate_verify_script(self) -> str:
        """검증 스크립트 생성"""
        return '''#!/bin/bash
# Blacklist Installation Verification Script

echo "🔍 Verifying Blacklist installation..."

# Check Python dependencies
echo "Checking Python dependencies..."
python3 -c "import flask, redis, requests" && echo "  ✓ Core Python packages OK"

# Check Docker
echo "Checking Docker..."
docker --version && echo "  ✓ Docker OK"

# Check system services
echo "Checking system services..."
systemctl is-active docker >/dev/null && echo "  ✓ Docker service OK"

echo "✅ Verification completed!"
'''

    def _save_manifest(self):
        """매니페스트 저장"""
        self.log_progress("Saving package manifest...")

        manifest_file = self.package_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)

        print(f"   ✓ Manifest saved: {manifest_file}")

    def _create_final_package(self) -> bool:
        """최종 패키지 생성"""
        self.log_progress("Creating final package...")

        package_file = self.output_dir / \
            f"{self.package_name}-v{self.version}.tar.gz"

        try:
            with tarfile.open(package_file, 'w:gz') as tar:
                tar.add(self.package_dir, arcname=self.package_dir.name)

            # 패키지 정보 출력
            size_mb = round(package_file.stat().st_size / (1024 * 1024), 2)
            print(f"\n🎉 Package created successfully!")
            print(f"   📦 File: {package_file}")
            print(f"   💾 Size: {size_mb} MB")

            return True

        except Exception as e:
            print(f"❌ Failed to create package: {e}")
            return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='Create offline deployment package')
    parser.add_argument(
        '--output',
        '-o',
        default='dist',
        help='Output directory')
    parser.add_argument(
        '--no-source',
        action='store_true',
        help='Exclude source code')

    args = parser.parse_args()

    builder = OfflinePackageBuilder(
        output_dir=args.output,
        include_source=not args.no_source
    )

    success = builder.build_package()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
