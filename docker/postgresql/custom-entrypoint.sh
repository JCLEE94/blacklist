#!/bin/bash
# Custom PostgreSQL Entrypoint for Blacklist System

set -e

# 로고 출력
cat << 'EOF'
 ____  _            _    _ _     _     ____           ____  
| __ )| | __ _  ___| | _| (_)___| |_  |  _ \ ___  ___| __ ) 
|  _ \| |/ _` |/ __| |/ / | / __| __| | |_) / _ \/ __|  _ \ 
| |_) | | (_| | (__|   <| | \__ \ |_  |  __/\___/\__ \ |_) |
|____/|_|\__,_|\___|_|\_\_|_|___/\__| |_|  \___/|___/____/ 

Custom PostgreSQL for Blacklist IP Management System
Version: 1.0.0
EOF

echo "🚀 Starting Custom PostgreSQL Server..."
echo "📊 Configuration: /etc/postgresql/postgresql.conf"
echo "💾 Data Directory: $PGDATA"
echo "🗄️ Database: $POSTGRES_DB"
echo "👤 User: $POSTGRES_USER"

# 환경변수 검증
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "❌ Error: POSTGRES_PASSWORD is not set"
    exit 1
fi

if [ "$POSTGRES_PASSWORD" = "blacklist_password_change_me" ]; then
    echo "⚠️ Warning: Using default password - change in production!"
fi

# 데이터 디렉토리 권한 확인
if [ ! -d "$PGDATA" ]; then
    echo "📁 Creating data directory: $PGDATA"
    mkdir -p "$PGDATA"
fi

chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

# 설정 파일 권한
chown postgres:postgres /etc/postgresql/postgresql.conf

echo "✅ PostgreSQL configuration completed"
echo "🎯 Starting PostgreSQL server with custom configuration..."

# PostgreSQL 기본 entrypoint 실행
exec docker-entrypoint.sh "$@"