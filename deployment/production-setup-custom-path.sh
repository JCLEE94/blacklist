#!/bin/bash

# 운영 환경 Watchtower 자동 배포 설정 스크립트 (커스텀 경로)

echo "🚀 운영 환경 Blacklist 시스템 설치 시작..."

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 설치 경로
INSTALL_PATH="/var/services/homes/docker/app/blacklist"

# 기본 디렉토리 생성
echo -e "${YELLOW}📁 디렉토리 구조 생성 중...${NC}"
mkdir -p ${INSTALL_PATH}/{instance,logs,data,config}
cd ${INSTALL_PATH}

# watchtower 인증 설정
echo -e "${YELLOW}🔐 레지스트리 인증 설정 중...${NC}"
REGISTRY_USER="qws941"
REGISTRY_PASS="bingogo1l7!"
AUTH_STRING=$(echo -n "${REGISTRY_USER}:${REGISTRY_PASS}" | base64)

cat > config/watchtower-config.json << EOF
{
  "auths": {
    "registry.jclee.me": {
      "auth": "${AUTH_STRING}"
    }
  }
}
EOF

chmod 600 config/watchtower-config.json
echo -e "${GREEN}✅ 인증 설정 완료${NC}"

# 환경 변수 파일 생성
echo -e "${YELLOW}🔧 환경 변수 설정 중...${NC}"
cat > .env.production << 'EOF'
# Production Environment Variables
PORT=8541
FLASK_ENV=production
TZ=Asia/Seoul
REDIS_URL=redis://blacklist-redis:6379/0

# Nextrade Credentials (All Services)
NEXTRADE_USERNAME=nextrade
NEXTRADE_PASSWORD=Sprtmxm1@3

# Service Specific
REGTECH_USERNAME=nextrade
REGTECH_PASSWORD=Sprtmxm1@3
SECUDIUM_USERNAME=nextrade
SECUDIUM_PASSWORD=Sprtmxm1@3
BLACKLIST_USERNAME=nextrade
BLACKLIST_PASSWORD=Sprtmxm1@3
ADMIN_PASSWORD=Sprtmxm1@3

# Security Keys
SECRET_KEY=blacklist-prod-secret-key-2025
JWT_SECRET_KEY=blacklist-jwt-secret-key-2025
API_SECRET_KEY=blacklist-api-secret-key-2025
FORCE_HTTPS=false
EOF

chmod 600 .env.production
echo -e "${GREEN}✅ 환경 변수 설정 완료${NC}"

# Watchtower 포함 docker-compose 파일 생성
echo -e "${YELLOW}📝 Docker Compose 파일 생성 중...${NC}"
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  blacklist-app:
    image: registry.jclee.me/blacklist-management:latest
    container_name: blacklist-app
    restart: unless-stopped
    ports:
      - "2541:8541"
    env_file:
      - .env.production
    volumes:
      - ./instance:/app/instance
      - ./logs:/app/logs
      - ./data:/app/data
    networks:
      - blacklist-net
    depends_on:
      - blacklist-redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8541/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  blacklist-redis:
    image: redis:7-alpine
    container_name: blacklist-redis
    restart: unless-stopped
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru --appendonly yes
    networks:
      - blacklist-net
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./config/watchtower-config.json:/config.json:ro
    environment:
      - WATCHTOWER_POLL_INTERVAL=300
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_INCLUDE_STOPPED=false
      - WATCHTOWER_INCLUDE_RESTARTING=true
      - WATCHTOWER_LABEL_ENABLE=false  # 모든 컨테이너 감시
      - WATCHTOWER_ROLLING_RESTART=true
      - WATCHTOWER_TIMEOUT=120s
      - WATCHTOWER_NOTIFICATIONS_LEVEL=info
      - WATCHTOWER_NO_PULL=false
      - DOCKER_CONFIG=/config.json
      - TZ=Asia/Seoul
      - WATCHTOWER_SCOPE=registry.jclee.me  # jclee.me 이미지만 감시
    command: --interval 300 --cleanup --scope registry.jclee.me
    labels:
      - "com.centurylinklabs.watchtower.enable=false"

networks:
  blacklist-net:
    driver: bridge

volumes:
  redis-data:
    driver: local
EOF

echo -e "${GREEN}✅ Docker Compose 파일 생성 완료${NC}"

# 최초 이미지 pull
echo -e "${YELLOW}🐳 Docker 이미지 다운로드 중...${NC}"
docker pull registry.jclee.me/blacklist-management:latest

# 서비스 시작
echo -e "${YELLOW}🚀 서비스 시작 중...${NC}"
docker-compose up -d

# 상태 확인
echo -e "${YELLOW}📊 서비스 상태 확인...${NC}"
sleep 10
docker-compose ps

# 헬스 체크
echo -e "${YELLOW}🏥 헬스 체크 수행 중...${NC}"
sleep 5
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:2541/health)

if [ "$HEALTH_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ 서비스가 정상적으로 시작되었습니다!${NC}"
else
    echo -e "${RED}❌ 서비스 시작 실패. 로그를 확인하세요.${NC}"
    docker-compose logs --tail=50
fi

# 정보 출력
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Blacklist 시스템 설치 완료!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📍 설치 경로: ${INSTALL_PATH}"
echo "🌐 서비스 URL: http://$(hostname -I | awk '{print $1}'):2541"
echo "📊 API 문서: http://$(hostname -I | awk '{print $1}'):2541/api/docs"
echo ""
echo "📌 주요 명령어:"
echo "  - 상태 확인: cd ${INSTALL_PATH} && docker-compose ps"
echo "  - 로그 확인: cd ${INSTALL_PATH} && docker-compose logs -f"
echo "  - 서비스 재시작: cd ${INSTALL_PATH} && docker-compose restart"
echo "  - 서비스 중지: cd ${INSTALL_PATH} && docker-compose down"
echo ""
echo "🔄 Watchtower가 5분마다 자동으로 업데이트를 확인합니다."
echo ""

# systemd 서비스 생성 옵션
echo -e "${YELLOW}시스템 시작 시 자동 시작을 설정하시겠습니까? (y/n)${NC}"
read -r AUTOSTART

if [ "$AUTOSTART" = "y" ] || [ "$AUTOSTART" = "Y" ]; then
    cat > /etc/systemd/system/blacklist.service << EOF
[Unit]
Description=Blacklist Management System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${INSTALL_PATH}
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable blacklist.service
    echo -e "${GREEN}✅ 자동 시작 설정 완료${NC}"
fi

echo ""
echo -e "${GREEN}설치가 완료되었습니다!${NC}"