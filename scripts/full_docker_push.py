#!/usr/bin/env python3
"""
Full Docker Push Script - Real Automation System v11.1
전체 Docker 이미지 빌드 및 푸시 (Redis, PostgreSQL 포함)

This script builds and pushes all Docker images including Redis and PostgreSQL.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_command(cmd, description=""):
    """Run a shell command and return the result"""
    print(f"🔄 {description}")
    print(f"   $ {cmd}")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ {description} - 성공")
        if result.stdout.strip():
            print(f"   출력: {result.stdout.strip()[:200]}")
        return True
    else:
        print(f"❌ {description} - 실패")
        if result.stderr.strip():
            print(f"   오류: {result.stderr.strip()[:200]}")
        return False


def load_version():
    """Load current version"""
    version_file = Path(__file__).parent.parent / "version_info.json"
    if version_file.exists():
        with open(version_file, "r") as f:
            return json.load(f)["version"]
    return "1.0.latest"


def main():
    """Main full Docker push workflow"""
    print("🐳 전체 Docker 이미지 빌드 및 푸시 시작")
    print("=" * 60)

    version = load_version()
    registry = "registry.jclee.me"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")

    print(f"📌 버전: {version}")
    print(f"📦 레지스트리: {registry}")
    print(f"🕐 타임스탬프: {timestamp}")

    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Docker images to build and push
    docker_builds = [
        {
            "name": "blacklist",
            "dockerfile": "Dockerfile",
            "context": ".",
            "description": "메인 애플리케이션",
        },
        {
            "name": "blacklist-redis",
            "dockerfile": "docker/redis/Dockerfile",
            "context": "docker/redis/",
            "description": "커스텀 Redis",
        },
        {
            "name": "blacklist-postgresql",
            "dockerfile": "docker/postgresql/Dockerfile",
            "context": "docker/postgresql/",
            "description": "커스텀 PostgreSQL",
        },
    ]

    success_count = 0
    failed_builds = []

    # Check Docker daemon
    if not run_command("docker --version", "Docker 데몬 확인"):
        print("❌ Docker를 사용할 수 없습니다")
        sys.exit(1)

    # Docker login to registry
    print(f"\n🔐 {registry} 로그인 중...")
    if not run_command(
        f"echo 'bingogo1' | docker login {registry} --username admin --password-stdin",
        "Registry 로그인",
    ):
        print("⚠️ Registry 로그인 실패, 계속 진행...")

    for build_info in docker_builds:
        print(f"\n{'='*40}")
        print(f"🏗️ {build_info['description']} 빌드 시작")
        print(f"   이미지: {build_info['name']}")

        dockerfile_path = project_root / build_info["dockerfile"]
        context_path = project_root / build_info["context"]

        # Check if Dockerfile exists
        if not dockerfile_path.exists():
            print(f"⚠️ Dockerfile 없음: {dockerfile_path}")
            print(f"   기본 Dockerfile 생성 중...")
            create_default_dockerfile(build_info, dockerfile_path)

        # Build image with multiple tags
        image_tags = [
            f"{registry}/{build_info['name']}:latest",
            f"{registry}/{build_info['name']}:{version}",
            f"{registry}/{build_info['name']}:{timestamp}",
        ]

        tag_args = " ".join([f"-t {tag}" for tag in image_tags])

        build_cmd = f"docker build {tag_args} -f {dockerfile_path} {context_path}"

        if run_command(build_cmd, f"{build_info['name']} 이미지 빌드"):
            print(f"✅ {build_info['name']} 빌드 성공")

            # Push all tags
            push_success = True
            for tag in image_tags:
                if not run_command(f"docker push {tag}", f"{tag} 푸시"):
                    push_success = False

            if push_success:
                print(f"✅ {build_info['name']} 모든 태그 푸시 성공")
                success_count += 1
            else:
                print(f"⚠️ {build_info['name']} 일부 푸시 실패")
                failed_builds.append(build_info["name"])
        else:
            print(f"❌ {build_info['name']} 빌드 실패")
            failed_builds.append(build_info["name"])

    # Summary
    print("\n" + "=" * 60)
    print("📊 전체 Docker 푸시 결과:")
    print(f"✅ 성공: {success_count}/{len(docker_builds)}개")

    if failed_builds:
        print(f"❌ 실패: {failed_builds}")

    # Update version_info.json with deployment info
    update_version_info(version, success_count, len(docker_builds))

    # Git commit the changes
    if success_count > 0:
        commit_message = f"""feat: full Docker deployment v{version}

🐳 Real Automation System v11.1 - Complete Docker Push
- 메인 애플리케이션: blacklist:{version}
- Redis: blacklist-redis:{version} 
- PostgreSQL: blacklist-postgresql:{version}

Success: {success_count}/{len(docker_builds)} images
Registry: {registry}
Timestamp: {timestamp}"""

        run_command("git add .", "Git 변경사항 스테이징")
        run_command(f'git commit -m "{commit_message}"', "Git 커밋")
        run_command("git push origin main", "Git 푸시")

        print("✅ Git 커밋 및 푸시 완료")

    print(f"\n🎯 전체 Docker 이미지 배포 완료!")
    print(f"🌐 확인: https://registry.jclee.me")


def create_default_dockerfile(build_info, dockerfile_path):
    """Create a default Dockerfile if one doesn't exist"""
    dockerfile_path.parent.mkdir(parents=True, exist_ok=True)

    if build_info["name"] == "blacklist-redis":
        content = """FROM redis:7-alpine

# Copy custom Redis configuration
COPY redis.conf /usr/local/etc/redis/redis.conf
COPY custom-entrypoint.sh /usr/local/bin/

# Make entrypoint executable
RUN chmod +x /usr/local/bin/custom-entrypoint.sh

# Use custom entrypoint
ENTRYPOINT ["/usr/local/bin/custom-entrypoint.sh"]
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD redis-cli ping | grep PONG

EXPOSE 6379"""

    elif build_info["name"] == "blacklist-postgresql":
        content = """FROM postgres:15-alpine

# Copy custom PostgreSQL configuration
COPY postgresql.conf /etc/postgresql/postgresql.conf
COPY init-scripts/ /docker-entrypoint-initdb.d/
COPY custom-entrypoint.sh /usr/local/bin/

# Make scripts executable
RUN chmod +x /usr/local/bin/custom-entrypoint.sh
RUN chmod +x /docker-entrypoint-initdb.d/*.sql || true

# Environment variables
ENV POSTGRES_DB=blacklist
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres
ENV PGDATA=/var/lib/postgresql/data/pgdata

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \\
    CMD pg_isready -U $POSTGRES_USER -d $POSTGRES_DB

EXPOSE 5432"""

    else:
        content = """FROM python:3.11-alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache gcc musl-dev postgresql-dev

# Copy requirements and install Python dependencies  
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser -D -s /bin/sh appuser
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:2542/health || exit 1

EXPOSE 2542
CMD ["python", "main.py"]"""

    with open(dockerfile_path, "w") as f:
        f.write(content)

    print(f"   ✅ 기본 Dockerfile 생성: {dockerfile_path}")


def update_version_info(version, success_count, total_count):
    """Update version_info.json with deployment information"""
    version_file = Path(__file__).parent.parent / "version_info.json"

    if version_file.exists():
        with open(version_file, "r") as f:
            version_info = json.load(f)
    else:
        version_info = {}

    version_info.update(
        {
            "version": version,
            "last_docker_deployment": datetime.now().isoformat(),
            "docker_images_deployed": success_count,
            "docker_images_total": total_count,
            "deployment_success_rate": f"{success_count/total_count*100:.1f}%",
            "registry": "registry.jclee.me",
            "automation_system": "Real Automation System v11.1",
        }
    )

    with open(version_file, "w") as f:
        json.dump(version_info, f, indent=2)

    print(f"✅ version_info.json 업데이트 완료")


if __name__ == "__main__":
    main()
