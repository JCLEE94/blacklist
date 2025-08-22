#!/bin/bash
# Volume Cleanup Script for Blacklist Docker Optimization
# Version: v1.0.37

set -euo pipefail

echo "🔄 Docker 볼륨 정리 시작..."

# 현재 실행 중인 컨테이너 확인
echo "📋 현재 실행 중인 Blacklist 컨테이너 확인..."
RUNNING_CONTAINERS=$(docker ps --filter "name=blacklist" --format "table {{.Names}}\t{{.Status}}" || true)
if [[ -n "$RUNNING_CONTAINERS" ]]; then
    echo "$RUNNING_CONTAINERS"
    echo ""
    echo "⚠️  실행 중인 컨테이너가 있습니다. 먼저 중지해주세요:"
    echo "   docker-compose down"
    echo ""
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 작업이 취소되었습니다."
        exit 1
    fi
fi

# 현재 볼륨 상태 출력
echo "📋 현재 Blacklist 관련 볼륨 목록:"
docker volume ls | grep blacklist | sort

echo ""
echo "🔍 볼륨 사용량 분석..."

# 각 볼륨의 크기 확인 함수
check_volume_size() {
    local volume_name=$1
    if docker volume inspect "$volume_name" &>/dev/null; then
        local mount_point=$(docker volume inspect "$volume_name" | jq -r '.[0].Mountpoint')
        if [[ -d "$mount_point" ]]; then
            local size=$(du -sh "$mount_point" 2>/dev/null | cut -f1 || echo "N/A")
            echo "  $volume_name: $size"
        else
            echo "  $volume_name: 마운트 포인트 없음"
        fi
    fi
}

# 볼륨 크기 확인
echo "📊 볼륨별 사용량:"
for volume in blacklist-data blacklist_data blacklist-logs blacklist-postgresql-data blacklist_postgresql_data blacklist-redis-data blacklist_redis_data; do
    check_volume_size "$volume"
done

echo ""
echo "🔄 중복 볼륨 정리 계획:"
echo "  유지할 볼륨 (하이픈 형식):"
echo "    - blacklist-data"
echo "    - blacklist-logs" 
echo "    - blacklist-postgresql-data"
echo "    - blacklist-redis-data"
echo ""
echo "  삭제할 볼륨 (언더스코어 형식):"
echo "    - blacklist_data"
echo "    - blacklist_postgresql_data" 
echo "    - blacklist_redis_data"

echo ""
read -p "볼륨 정리를 진행하시겠습니까? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 작업이 취소되었습니다."
    exit 1
fi

# 데이터 백업 함수
backup_volume_data() {
    local old_volume=$1
    local new_volume=$2
    
    echo "📦 $old_volume → $new_volume 데이터 마이그레이션..."
    
    # 임시 컨테이너로 데이터 복사
    if docker volume inspect "$old_volume" &>/dev/null && docker volume inspect "$new_volume" &>/dev/null; then
        docker run --rm \
            -v "$old_volume":/source \
            -v "$new_volume":/target \
            alpine:latest \
            sh -c "cp -a /source/. /target/ 2>/dev/null || true"
        echo "✅ $old_volume 데이터 마이그레이션 완료"
    else
        echo "⚠️  볼륨 중 하나가 존재하지 않음: $old_volume 또는 $new_volume"
    fi
}

# 필요한 새 볼륨 생성
echo "🔨 표준 볼륨 생성..."
docker volume create blacklist-data 2>/dev/null || echo "blacklist-data 이미 존재"
docker volume create blacklist-logs 2>/dev/null || echo "blacklist-logs 이미 존재"
docker volume create blacklist-postgresql-data 2>/dev/null || echo "blacklist-postgresql-data 이미 존재" 
docker volume create blacklist-redis-data 2>/dev/null || echo "blacklist-redis-data 이미 존재"

# 데이터 마이그레이션 (안전하게)
if docker volume inspect blacklist_data &>/dev/null; then
    backup_volume_data blacklist_data blacklist-data
fi

if docker volume inspect blacklist_postgresql_data &>/dev/null; then
    backup_volume_data blacklist_postgresql_data blacklist-postgresql-data
fi

if docker volume inspect blacklist_redis_data &>/dev/null; then
    backup_volume_data blacklist_redis_data blacklist-redis-data  
fi

# 중복 볼륨 삭제
echo "🗑️  중복 볼륨 삭제..."
for volume in blacklist_data blacklist_postgresql_data blacklist_redis_data; do
    if docker volume inspect "$volume" &>/dev/null; then
        echo "🗑️  $volume 삭제 중..."
        docker volume rm "$volume" 2>/dev/null || echo "⚠️  $volume 삭제 실패 (사용 중일 수 있음)"
    else
        echo "⚠️  $volume 이미 존재하지 않음"
    fi
done

# 고아 볼륨 정리
echo "🧹 고아 볼륨 정리..."
docker volume prune -f

# 최종 상태 확인
echo ""
echo "✅ 볼륨 정리 완료!"
echo "📋 최종 Blacklist 볼륨 목록:"
docker volume ls | grep blacklist | sort

echo ""
echo "🎯 권장 사항:"
echo "  1. 새로운 docker-compose.yml 사용"
echo "  2. 환경별 .env 파일 활용"
echo "  3. 볼륨 이름 표준화 (하이픈 사용)"
echo ""
echo "🚀 이제 다음 명령으로 서비스를 시작할 수 있습니다:"
echo "  docker-compose --env-file .env.production up -d"