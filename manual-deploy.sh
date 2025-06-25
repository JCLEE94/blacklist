#!/bin/bash
# 수동 배포 스크립트 - CI/CD 우회용

set -e

echo "🚀 수동 배포 시작..."

# 현재 커밋 해시 가져오기
COMMIT_HASH=$(git rev-parse --short HEAD)
echo "현재 커밋: $COMMIT_HASH"

# Docker 이미지 빌드
echo "📦 Docker 이미지 빌드 중..."
docker build -t registry.jclee.me/blacklist:$COMMIT_HASH .
docker tag registry.jclee.me/blacklist:$COMMIT_HASH registry.jclee.me/blacklist:latest

echo "🔑 Docker Registry 로그인..."
echo "$REGISTRY_PASSWORD" | docker login registry.jclee.me -u "$REGISTRY_USERNAME" --password-stdin

echo "📤 이미지 푸시 중..."
docker push registry.jclee.me/blacklist:$COMMIT_HASH
docker push registry.jclee.me/blacklist:latest

echo "🔄 프로덕션 서버에 배포 신호 전송..."
# Watchtower에게 업데이트 신호 (label 기반)
curl -X POST "https://registry.jclee.me:1111/v1/update" \
  -H "Authorization: Bearer watchtower" \
  -H "Content-Type: application/json" \
  -d '{"name": "blacklist"}' 2>/dev/null || echo "Watchtower API 호출 실패 (정상적일 수 있음)"

echo "⏳ 배포 대기 (60초)..."
sleep 60

echo "✅ 배포 완료! 서비스 상태 확인:"
curl -s https://blacklist.jclee.me/health | python3 -m json.tool

echo ""
echo "🧪 수집기 테스트:"
curl -s -X POST https://blacklist.jclee.me/api/collection/secudium/trigger \
  -H "Content-Type: application/json" -d '{}' | head -c 500

echo ""
echo "📊 통계 확인:"
curl -s https://blacklist.jclee.me/api/stats | python3 -m json.tool