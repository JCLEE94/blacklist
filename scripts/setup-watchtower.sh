#!/bin/bash

# Watchtower 설정 스크립트

echo "🐳 Watchtower 설정 시작..."

# 레지스트리 자격증명 생성
REGISTRY_USER="qws941"
REGISTRY_PASS="bingogo1l7!"
AUTH_STRING=$(echo -n "${REGISTRY_USER}:${REGISTRY_PASS}" | base64)

# watchtower-config.json 생성
cat > watchtower-config.json << EOF
{
  "auths": {
    "registry.jclee.me": {
      "auth": "${AUTH_STRING}"
    }
  }
}
EOF

echo "✅ watchtower-config.json 생성 완료"

# 권한 설정
chmod 600 watchtower-config.json
echo "✅ 설정 파일 권한 설정 완료"

# 기존 컨테이너 정리 (있을 경우)
echo "🧹 기존 컨테이너 정리 중..."
docker-compose -f docker-compose.watchtower.yml down 2>/dev/null || true

# 볼륨 생성 (없을 경우)
docker volume create redis-data 2>/dev/null || true

# 인스턴스 디렉토리 생성
mkdir -p instance logs

echo "🚀 Watchtower와 애플리케이션 시작..."
docker-compose -f docker-compose.watchtower.yml up -d

# 상태 확인
echo ""
echo "📊 컨테이너 상태:"
docker-compose -f docker-compose.watchtower.yml ps

echo ""
echo "✅ Watchtower 설정 완료!"
echo ""
echo "📌 사용 방법:"
echo "  - 시작: docker-compose -f docker-compose.watchtower.yml up -d"
echo "  - 중지: docker-compose -f docker-compose.watchtower.yml down"
echo "  - 로그: docker-compose -f docker-compose.watchtower.yml logs -f"
echo "  - Watchtower 로그: docker logs watchtower -f"
echo ""
echo "🔄 Watchtower는 5분마다 레지스트리를 확인하여 새 이미지가 있으면 자동으로 업데이트합니다."