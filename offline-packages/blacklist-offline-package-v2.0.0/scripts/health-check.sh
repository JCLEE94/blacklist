#!/bin/bash
# 블랙리스트 시스템 헬스체크 스크립트

set -e

INSTALL_DIR="${1:-/opt/blacklist}"
API_URL="http://localhost:32542"

echo "🏥 블랙리스트 시스템 헬스체크"
echo "================================"

# 서비스 상태 확인
echo "📊 서비스 상태:"
if systemctl is-active --quiet blacklist; then
    echo "  ✅ systemd 서비스: 실행 중"
else
    echo "  ❌ systemd 서비스: 중지됨"
fi

# Docker 컨테이너 상태 확인
echo "🐳 Docker 컨테이너 상태:"
cd "$INSTALL_DIR"
docker-compose ps

# API 응답 확인
echo "🌐 API 응답 확인:"
if curl -s -f "$API_URL/health" >/dev/null; then
    echo "  ✅ 헬스 엔드포인트: 정상"
    
    # 상세 상태 확인
    HEALTH_DATA=$(curl -s "$API_URL/api/health" | python3 -m json.tool 2>/dev/null || echo "{}")
    echo "  📊 시스템 상태: $(echo "$HEALTH_DATA" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"
else
    echo "  ❌ 헬스 엔드포인트: 응답 없음"
fi

# 데이터베이스 확인
echo "🗄️ 데이터베이스 상태:"
if [[ -f "$INSTALL_DIR/instance/blacklist.db" ]]; then
    DB_SIZE=$(du -h "$INSTALL_DIR/instance/blacklist.db" | cut -f1)
    echo "  ✅ 데이터베이스: 존재 (크기: $DB_SIZE)"
else
    echo "  ❌ 데이터베이스: 없음"
fi

# 포트 확인
echo "🔌 포트 상태:"
if netstat -tuln | grep -q ":32542 "; then
    echo "  ✅ 포트 32542: 열림"
else
    echo "  ❌ 포트 32542: 닫힘"
fi

# 로그 확인
echo "📝 최근 로그 (마지막 10줄):"
journalctl -u blacklist --no-pager -n 10

echo "================================"
echo "헬스체크 완료"
