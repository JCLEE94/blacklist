#!/bin/bash

# Verify registry.jclee.me deployment and Watchtower status
# Version: v1.3.4

set -e

echo "🔍 registry.jclee.me 배포 상태 확인 중..."

# Configuration
REGISTRY="registry.jclee.me"
IMAGE_NAME="blacklist"
LIVE_URL="https://blacklist.jclee.me"
LOCAL_URL="http://localhost:32542"
VERSION=$(cat config/VERSION 2>/dev/null | head -1 || echo "1.3.4")

echo "📋 확인 대상:"
echo "  - 레지스트리: ${REGISTRY}"
echo "  - 이미지: ${IMAGE_NAME}:v${VERSION}"
echo "  - 라이브 URL: ${LIVE_URL}"
echo "  - 로컬 URL: ${LOCAL_URL}"

# 1. Registry 이미지 확인
echo ""
echo "📦 1. 레지스트리 이미지 확인"
echo "   💡 참고: AI는 registry.jclee.me에 직접 접근할 수 없습니다"
echo "   🔗 수동 확인: https://registry.jclee.me/v2/${IMAGE_NAME}/tags/list"

# 2. 로컬 이미지 확인
echo ""
echo "📦 2. 로컬 이미지 확인"
if docker images | grep -q "${REGISTRY}/${IMAGE_NAME}"; then
    echo "✅ 로컬 이미지 존재"
    docker images | grep "${REGISTRY}/${IMAGE_NAME}" | head -5
else
    echo "❌ 로컬 이미지 없음"
fi

# 3. 라이브 시스템 간접 확인
echo ""
echo "🌐 3. 라이브 시스템 간접 확인"
echo "   💡 AI는 운영서버에 직접 접근할 수 없어 간접적으로만 확인"

# Check if curl is available
if command -v curl >/dev/null 2>&1; then
    echo "   🔍 헬스체크 시도 중..."
    if curl -s --max-time 10 "${LIVE_URL}/health" >/dev/null 2>&1; then
        echo "✅ 라이브 시스템 응답 확인됨"
        echo "   🔗 직접 확인: ${LIVE_URL}/health"
    else
        echo "⚠️  라이브 시스템 응답 확인 불가 (네트워크 제한 가능)"
        echo "   🔗 수동 확인: ${LIVE_URL}/health"
    fi
else
    echo "   ⚠️  curl 없음, 수동 확인 필요"
    echo "   🔗 수동 확인: ${LIVE_URL}/health"
fi

# 4. Docker Compose 상태 확인
echo ""
echo "🐳 4. 로컬 Docker Compose 상태"
COMPOSE_FILE="/home/jclee/app/blacklist/deployments/docker-compose/docker-compose.yml"

if [ -f "${COMPOSE_FILE}" ]; then
    echo "✅ Docker Compose 파일 존재: ${COMPOSE_FILE}"
    
    # Check if containers are running locally
    if docker ps | grep -q "blacklist"; then
        echo "✅ 로컬 blacklist 컨테이너 실행 중"
        docker ps | grep "blacklist"
    else
        echo "❌ 로컬 blacklist 컨테이너 미실행"
    fi
else
    echo "❌ Docker Compose 파일 없음"
fi

# 5. Watchtower 모니터링 안내
echo ""
echo "⏰ 5. Watchtower 자동 배포 모니터링"
echo "   💡 다음 명령어로 Watchtower 상태를 확인하세요:"
echo ""
echo "   # Watchtower 로그 실시간 모니터링"
echo "   docker logs watchtower -f"
echo ""
echo "   # 컨테이너 상태 확인"
echo "   docker ps | grep blacklist"
echo ""
echo "   # 업데이트된 이미지 확인"
echo "   docker images | grep registry.jclee.me/blacklist"
echo ""
echo "   # 애플리케이션 로그 확인"
echo "   docker logs blacklist -f"

# 6. 배포 검증 체크리스트
echo ""
echo "✅ 배포 검증 체크리스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "□ 1. 이미지 빌드 완료"
echo "□ 2. registry.jclee.me 푸시 완료"
echo "□ 3. Watchtower가 새 이미지 감지"
echo "□ 4. 컨테이너 자동 재시작 완료"
echo "□ 5. 헬스체크 통과: ${LIVE_URL}/health"
echo "□ 6. API 정상 동작: ${LIVE_URL}/api/blacklist/active"
echo "□ 7. 대시보드 접근: ${LIVE_URL}/dashboard"
echo "□ 8. 로그 확인: 오류 없음"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 7. 수동 확인 링크 제공
echo ""
echo "🔗 수동 확인 링크"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "라이브 시스템:"
echo "  - 메인 페이지: ${LIVE_URL}/"
echo "  - 헬스체크: ${LIVE_URL}/health"
echo "  - API 상태: ${LIVE_URL}/api/health"
echo "  - 블랙리스트: ${LIVE_URL}/api/blacklist/active"
echo "  - 대시보드: ${LIVE_URL}/dashboard"
echo "  - 버전 정보: ${LIVE_URL}/api/version"
echo ""
echo "레지스트리:"
echo "  - 이미지 목록: https://registry.jclee.me/v2/${IMAGE_NAME}/tags/list"
echo "  - Redis 이미지: https://registry.jclee.me/v2/${IMAGE_NAME}-redis/tags/list"
echo "  - PostgreSQL 이미지: https://registry.jclee.me/v2/${IMAGE_NAME}-postgresql/tags/list"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 8. 다음 단계 안내
echo ""
echo "📋 다음 단계"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "자동 배포 (Watchtower):"
echo "  1. Watchtower가 5분 이내에 새 이미지 감지"
echo "  2. 기존 컨테이너 자동 종료"
echo "  3. 새 이미지로 컨테이너 재시작"
echo "  4. 헬스체크 자동 실행"
echo ""
echo "수동 배포 (필요시):"
echo "  1. docker-compose -f ${COMPOSE_FILE} pull"
echo "  2. docker-compose -f ${COMPOSE_FILE} up -d"
echo ""
echo "K8s 배포 (선택사항):"
echo "  1. 생성된 K8s 매니페스트 확인: k8s-manifests/"
echo "  2. kubectl apply -f k8s-manifests/deployment-v${VERSION}.yaml"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "🎉 registry.jclee.me 배포 상태 확인 완료!"
echo "   💡 실제 배포 상태는 위의 링크들을 통해 수동으로 확인하세요"