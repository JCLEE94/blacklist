#!/bin/bash
# Docker 바인드 마운트 → 볼륨 마이그레이션 래퍼 스크립트
# 사용법: ./migrate-to-volumes.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🐳 Docker 바인드 마운트 → 볼륨 마이그레이션"
echo "================================================"
echo
echo "이 스크립트는 다음 작업을 수행합니다:"
echo "1. 현재 실행 중인 서비스 중지"
echo "2. 바인드 마운트 데이터 백업"
echo "3. 네임드 볼륨 생성 및 데이터 이전"
echo "4. Docker Compose 파일 업데이트"
echo "5. 서비스 재시작 및 검증"
echo
echo "📋 발견된 바인드 마운트:"
echo "- ./monitoring/prometheus.yml"
echo "- ./monitoring/grafana/dashboards"
echo "- ./monitoring/grafana/datasources"
echo "- ./config/postgresql.conf"
echo "- /var/run/docker.sock (유지)"
echo "- ~/.docker/config.json (유지)"
echo
echo "📦 생성될 네임드 볼륨:"
echo "- blacklist-prometheus-config"
echo "- blacklist-grafana-dashboards"
echo "- blacklist-grafana-datasources"
echo "- blacklist-postgresql-config"
echo

# 마이그레이션 스크립트 실행
exec "$SCRIPT_DIR/scripts/docker-volume-migration.sh"