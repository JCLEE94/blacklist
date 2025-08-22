#!/bin/bash
# Migration Test Script for Optimized Docker Setup
# Version: v1.0.37

set -euo pipefail

echo "🔄 최적화된 Docker 설정 마이그레이션 테스트"
echo ""

# 1. 현재 상태 백업
echo "📦 현재 상태 백업 중..."
mkdir -p ./migration-backup/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./migration-backup/$(date +%Y%m%d_%H%M%S)"

# PostgreSQL 데이터 백업
if docker ps --filter "name=blacklist-postgresql" | grep -q "Up"; then
    echo "🗄️  PostgreSQL 데이터 백업 중..."
    docker exec blacklist-postgresql pg_dump -U blacklist_user blacklist > "$BACKUP_DIR/postgresql_backup.sql" 2>/dev/null || echo "백업 실패 - 빈 데이터베이스일 수 있음"
fi

# 2. 기존 서비스 정리
echo "🛑 기존 서비스 중지 중..."
docker-compose down 2>/dev/null || true

# 3. 새로운 설정으로 시작
echo "🚀 최적화된 설정으로 서비스 시작..."

# 환경 파일 확인
if [[ ! -f ".env.production" ]]; then
    echo "❌ .env.production 파일이 없습니다!"
    exit 1
fi

# 새로운 docker-compose.yml 사용
echo "🔧 새로운 docker-compose.yml 테스트 중..."
docker-compose --env-file .env.production config > ./test-compose-output.yml
echo "✅ Docker Compose 구성 검증 완료"

# 서비스 시작
echo "🚀 서비스 시작 중..."
docker-compose --env-file .env.production up -d

# 4. 헬스체크 대기
echo "⏳ 서비스 시작 대기 중..."
sleep 30

# 5. 상태 확인
echo "🏥 헬스체크 실행 중..."
./scripts/docker-manager.sh health

# 6. 접속 테스트
echo "🌐 접속 테스트 중..."
if curl -f http://localhost:32542/health &>/dev/null; then
    echo "✅ 웹 서비스 정상 응답"
else
    echo "❌ 웹 서비스 응답 없음"
    echo "로그 확인:"
    docker logs blacklist --tail=10
fi

# 7. API 테스트
echo "📡 API 테스트 중..."
if curl -f http://localhost:32542/api/health &>/dev/null; then
    echo "✅ API 정상 응답"
else
    echo "❌ API 응답 없음"
fi

echo ""
echo "🎯 마이그레이션 테스트 완료!"
echo "📊 최종 상태:"
./scripts/docker-manager.sh status

echo ""
echo "🔧 다음 단계:"
echo "  1. 로그 확인: ./scripts/docker-manager.sh logs blacklist"
echo "  2. 전체 상태: ./scripts/docker-manager.sh health"
echo "  3. 접속 테스트: curl http://localhost:32542/health"