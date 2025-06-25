#!/bin/bash
# 긴급 배포 스크립트 - 로컬 이미지를 직접 export/import

set -e

IMAGE_NAME="registry.jclee.me/blacklist:manual-fix-20250626-0351"
EXPORT_FILE="blacklist-emergency-$(date +%Y%m%d-%H%M).tar"

echo "🚨 긴급 배포 시작..."
echo "이미지: $IMAGE_NAME"

# 1. Docker 이미지를 파일로 export
echo "📦 이미지 export 중..."
docker save $IMAGE_NAME > $EXPORT_FILE

echo "📏 Export 파일 크기:"
ls -lh $EXPORT_FILE

echo ""
echo "🔄 다음 단계 (프로덕션 서버에서 실행):"
echo "1. 이 파일을 프로덕션 서버로 전송"
echo "2. docker load < $EXPORT_FILE"
echo "3. docker tag $IMAGE_NAME registry.jclee.me/blacklist:latest"
echo "4. 컨테이너 재시작"

echo ""
echo "📋 프로덕션 서버 배포 명령어:"
echo "# 기존 컨테이너 정지"
echo "docker stop blacklist-app 2>/dev/null || true"
echo ""
echo "# 새 이미지로 실행"
echo "docker run -d --name blacklist-app-new \\"
echo "  -p 2541:2541 \\"
echo "  -v /app/blacklist/instance:/app/instance \\"
echo "  -v /app/blacklist/data:/app/data \\"
echo "  -e REGTECH_USERNAME=nextrade \\"
echo "  -e REGTECH_PASSWORD=Sprtmxm1@3 \\"
echo "  -e SECUDIUM_USERNAME=nextrade \\"
echo "  -e SECUDIUM_PASSWORD=Sprtmxm1@3 \\"
echo "  --restart unless-stopped \\"
echo "  $IMAGE_NAME"
echo ""
echo "# 기존 컨테이너 제거"  
echo "docker rm blacklist-app 2>/dev/null || true"
echo "docker rename blacklist-app-new blacklist-app"

echo ""
echo "✅ Export 완료: $EXPORT_FILE"