#!/bin/bash
# 강제 업데이트 스크립트 - 원격 Docker 명령 실행

set -e

echo "🔄 원격 컨테이너 강제 업데이트 시도..."

# GitHub Container Registry 시도
echo "📦 GitHub Container Registry에서 최신 이미지 pull 시도..."

# 이미지를 GitHub Container Registry로 푸시
docker tag registry.jclee.me/blacklist:latest ghcr.io/jclee94/blacklist:latest
docker tag registry.jclee.me/blacklist:latest ghcr.io/jclee94/blacklist:emergency-$(date +%Y%m%d)

echo "🔐 GitHub Container Registry 로그인 필요..."
echo "다음 명령어를 실행하세요:"
echo "echo \$GITHUB_TOKEN | docker login ghcr.io -u JCLEE94 --password-stdin"
echo "docker push ghcr.io/jclee94/blacklist:latest"
echo "docker push ghcr.io/jclee94/blacklist:emergency-$(date +%Y%m%d)"

echo ""
echo "🎯 원격 서버 업데이트 명령어:"
echo "ssh docker@registry.jclee.me -p 1112 << 'EOF'"
echo "# 최신 이미지 pull"
echo "docker pull ghcr.io/jclee94/blacklist:latest"
echo ""
echo "# 기존 컨테이너 중지"
echo "docker stop \$(docker ps -q --filter name=blacklist) 2>/dev/null || true"
echo ""
echo "# 새 컨테이너 실행"
echo "docker run -d --name blacklist-fixed \\"
echo "  -p 2541:2541 \\"
echo "  -v blacklist_instance:/app/instance \\"
echo "  -v blacklist_data:/app/data \\"
echo "  -e REGTECH_USERNAME=nextrade \\"
echo "  -e REGTECH_PASSWORD=Sprtmxm1@3 \\"
echo "  -e SECUDIUM_USERNAME=nextrade \\"
echo "  -e SECUDIUM_PASSWORD=Sprtmxm1@3 \\"
echo "  --restart unless-stopped \\"
echo "  --label com.centurylinklabs.watchtower.enable=true \\"
echo "  ghcr.io/jclee94/blacklist:latest"
echo ""
echo "# 기존 컨테이너 정리"
echo "docker container prune -f"
echo "EOF"

echo ""
echo "🔍 업데이트 확인:"
echo "curl -s https://blacklist.jclee.me/health"
echo "curl -s https://blacklist.jclee.me/api/collection/status"