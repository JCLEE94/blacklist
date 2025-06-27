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
# Watchtower webhook 호출
echo "🔔 Watchtower webhook 트리거..."
WEBHOOK_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST https://watchtower.jclee.me/v1/update \
  -H "Authorization: Bearer MySuperSecretToken12345" 2>&1 || echo "Failed")

HTTP_CODE=$(echo "$WEBHOOK_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Watchtower webhook 성공!"
else
  echo "⚠️ Watchtower webhook 응답: $HTTP_CODE"
fi

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