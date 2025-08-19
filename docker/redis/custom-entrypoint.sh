#!/bin/sh
# Custom Redis Entrypoint for Blacklist System

set -e

# 로고 출력
cat << 'EOF'
 ____  _            _    _ _     _     ____          _ _     
| __ )| | __ _  ___| | _| (_)___| |_  |  _ \ ___  __| (_)___ 
|  _ \| |/ _` |/ __| |/ / | / __| __| | |_) / _ \/ _` | / __|
| |_) | | (_| | (__|   <| | \__ \ |_  |  _ <  __/ (_| | \__ \
|____/|_|\__,_|\___|_|\_\_|_|___/\__| |_| \_\___|\__,_|_|___/

Custom Redis for Blacklist IP Management System
Version: 1.0.0
EOF

echo "🚀 Starting Custom Redis Server..."
echo "📊 Configuration: /usr/local/etc/redis/redis.conf"
echo "💾 Data Directory: /data"

# 환경변수 처리
if [ -n "$REDIS_PASSWORD" ]; then
    echo "🔒 Setting Redis password from environment variable"
    echo "requirepass $REDIS_PASSWORD" >> /usr/local/etc/redis/redis.conf
fi

if [ -n "$REDIS_MAXMEMORY" ]; then
    echo "💽 Setting max memory to: $REDIS_MAXMEMORY"
    sed -i "s/maxmemory 256mb/maxmemory $REDIS_MAXMEMORY/" /usr/local/etc/redis/redis.conf
fi

# 데이터 디렉토리 권한 확인
if [ ! -d /data ]; then
    mkdir -p /data
fi
chown -R redis:redis /data

# 설정 파일 권한
chown redis:redis /usr/local/etc/redis/redis.conf

echo "✅ Redis configuration completed"
echo "🎯 Starting Redis server with custom configuration..."

# Redis 서버 실행
exec "$@"