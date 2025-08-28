#!/bin/bash
# Docker 및 Watchtower 문제 해결 스크립트

echo "🔧 Docker 및 Watchtower 문제 해결 중..."
echo "============================================="

# 1. Docker 정보 확인
echo "📋 현재 Docker 환경:"
docker --version
docker-compose --version
echo ""

# 2. 로컬 테스트용 간소화된 compose 파일 생성
echo "📝 로컬 테스트용 compose 파일 생성..."
cat > docker-compose.local.yml << 'EOF'
version: '3.8'

services:
  blacklist:
    image: registry.jclee.me/qws941/blacklist:emergency
    container_name: blacklist-local
    restart: unless-stopped
    ports:
      - "2541:2541"
    environment:
      - FLASK_ENV=development
      - PORT=2541
      - HOST=0.0.0.0
      - FORCE_DISABLE_COLLECTION=true
      - COLLECTION_ENABLED=false
      - RESTART_PROTECTION=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2541/health"]
      interval: 30s
      timeout: 10s
      retries: 3
EOF

# 3. 로컬 테스트 실행
echo "🧪 로컬 테스트 실행..."
docker-compose -f docker-compose.local.yml down 2>/dev/null
docker-compose -f docker-compose.local.yml up -d

# 4. 서비스 시작 대기
echo "⏳ 서비스 시작 대기 (45초)..."
sleep 45

# 5. 헬스체크
echo "🔍 헬스체크 수행..."
if curl -s --connect-timeout 5 http://localhost:2541/health >/dev/null 2>&1; then
    echo "✅ 로컬 서비스 정상 응답!"
    echo "📊 헬스체크 결과:"
    curl -s http://localhost:2541/health | jq '.' 2>/dev/null || curl -s http://localhost:2541/health
else
    echo "❌ 로컬 서비스 응답 없음"
    echo "📋 컨테이너 로그 확인:"
    docker logs blacklist-local --tail 20
fi

# 6. Registry 로그인 테스트 (선택적)
echo ""
echo "🔐 Registry 접근 테스트:"
if docker pull registry.jclee.me/qws941/blacklist:latest 2>/dev/null; then
    echo "✅ Registry 접근 가능"
else
    echo "❌ Registry 접근 불가 - 인증 필요"
fi

echo ""
echo "🎯 결과 요약:"
echo "- 로컬 서비스: $(curl -s http://localhost:2541/health >/dev/null 2>&1 && echo '정상' || echo '비정상')"
echo "- Registry: $(docker pull registry.jclee.me/qws941/blacklist:latest >/dev/null 2>&1 && echo '접근가능' || echo '접근불가')"
echo ""
echo "💡 다음 단계:"
echo "1. 로컬 테스트: http://localhost:2541"
echo "2. Registry 인증 설정 필요시 Docker 로그인"
echo "3. 원격 서버 직접 배포 고려"