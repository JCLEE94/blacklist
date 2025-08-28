# RHEL8 설치 작업계획서
## Blacklist Management System v1.0.37

### 📋 시스템 요구사항

#### 하드웨어 요구사항
- **CPU**: 최소 4 Core (권장 8 Core)
- **RAM**: 최소 8GB (권장 16GB)
- **Storage**: 최소 100GB (SSD 권장)
- **Network**: 1Gbps Ethernet

#### 소프트웨어 요구사항
- **OS**: Red Hat Enterprise Linux 8.x
- **Python**: 3.9+ (RHEL8 기본 포함)
- **Container**: Docker CE 24.0+ 또는 Podman 4.0+
- **Git**: 2.31+ (RHEL8 기본 포함)

### 🔧 RHEL8 시스템 준비

#### 1. 시스템 업데이트
```bash
# 시스템 전체 업데이트
sudo dnf update -y

# 개발 도구 설치
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y git wget curl unzip

# Python 개발 도구
sudo dnf install -y python3 python3-pip python3-devel

# PostgreSQL 클라이언트 도구
sudo dnf install -y postgresql postgresql-contrib

# Redis 클라이언트 도구
sudo dnf install -y redis
```

#### 2. SELinux 설정
```bash
# SELinux 상태 확인
getenforce

# SELinux 정책 조정 (필요시)
sudo setsebool -P container_manage_cgroup true
sudo setsebool -P container_use_devices true

# Docker/Podman용 SELinux 컨텍스트
sudo semanage fcontext -a -t container_file_t "/opt/blacklist(/.*)?"
sudo restorecon -R /opt/blacklist
```

#### 3. 방화벽 설정
```bash
# 방화벽 포트 개방
sudo firewall-cmd --permanent --add-port=32542/tcp  # Blacklist App
sudo firewall-cmd --permanent --add-port=32543/tcp  # PostgreSQL
sudo firewall-cmd --permanent --add-port=6379/tcp   # Redis (내부)
sudo firewall-cmd --reload

# 서비스 등록
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 🐳 Container Runtime 설치

#### Option A: Docker CE 설치 (권장)
```bash
# Docker 저장소 추가
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo

# Docker CE 설치
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Docker 서비스 시작
sudo systemctl enable --now docker

# 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose 설치 확인
docker compose version
```

#### Option B: Podman 설치 (RHEL 기본)
```bash
# Podman 설치
sudo dnf install -y podman podman-compose podman-docker

# Docker 호환성 설정
sudo systemctl enable --now podman.socket
sudo systemctl enable --now podman-restart

# Podman-Docker 심볼릭 링크
sudo ln -sf /usr/bin/podman /usr/local/bin/docker
```

### 📁 디렉토리 구조 생성

```bash
# 애플리케이션 디렉토리 생성
sudo mkdir -p /opt/blacklist/{data,logs,config,backups}
sudo mkdir -p /opt/blacklist/postgresql-data
sudo mkdir -p /opt/blacklist/redis-data

# 권한 설정
sudo chown -R $USER:$USER /opt/blacklist
chmod 755 /opt/blacklist
chmod 700 /opt/blacklist/data
chmod 700 /opt/blacklist/postgresql-data
chmod 700 /opt/blacklist/redis-data
```

### 🔐 보안 설정

#### 1. SSL/TLS 인증서 (선택사항)
```bash
# Let's Encrypt 설치 (공인 도메인 사용시)
sudo dnf install -y certbot

# 자체 서명 인증서 생성
sudo mkdir -p /opt/blacklist/certs
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /opt/blacklist/certs/blacklist.key \
    -out /opt/blacklist/certs/blacklist.crt \
    -subj "/C=KR/ST=Seoul/L=Seoul/O=Company/CN=blacklist.company.local"

sudo chown -R $USER:$USER /opt/blacklist/certs
chmod 600 /opt/blacklist/certs/*.key
chmod 644 /opt/blacklist/certs/*.crt
```

#### 2. 네트워크 보안
```bash
# Private Docker 네트워크 생성
docker network create --driver bridge blacklist-net

# 네트워크 보안 규칙
sudo iptables -A INPUT -p tcp --dport 32542 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 32543 -s 172.20.0.0/16 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

### 📦 Blacklist 애플리케이션 설치

#### 1. 오프라인 패키지 설치 (권장)
```bash
# 패키지 다운로드 (인터넷 연결된 시스템에서)
wget https://github.com/qws941/blacklist/releases/latest/download/blacklist-rhel8-package.tar.gz

# 패키지 복사 (사내망으로)
scp blacklist-rhel8-package.tar.gz user@rhel8-server:/tmp/

# 서버에서 설치
cd /tmp
tar -xzf blacklist-rhel8-package.tar.gz
cd blacklist-rhel8-package
sudo ./install-rhel8.sh
```

#### 2. Git Clone 설치 (개발/테스트용)
```bash
# Git 저장소 클론
cd /opt
sudo git clone https://github.com/qws941/blacklist.git
sudo chown -R $USER:$USER /opt/blacklist
cd /opt/blacklist

# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# 의존성 설치
pip install -r requirements.txt
```

### ⚙️ 환경 설정

#### 1. 환경변수 파일 생성
```bash
# .env 파일 생성
cd /opt/blacklist
cp config/.env.example .env

# 설정 편집
cat > .env << 'EOF'
# RHEL8 Production Configuration
FLASK_ENV=production
PORT=2542
DEBUG=false

# Database (PostgreSQL)
DATABASE_URL=postgresql://blacklist_user:CHANGE_PASSWORD@localhost:5432/blacklist

# Cache (Redis)
REDIS_URL=redis://localhost:6379/0

# Security Keys (반드시 변경)
SECRET_KEY=CHANGE_THIS_TO_RANDOM_STRING_IN_PRODUCTION
JWT_SECRET_KEY=CHANGE_THIS_TO_ANOTHER_RANDOM_STRING
DEFAULT_API_KEY=blk_GENERATE_NEW_API_KEY_HERE

# Admin Account
ADMIN_USERNAME=admin
ADMIN_PASSWORD=CHANGE_THIS_PASSWORD

# Collection Settings
COLLECTION_ENABLED=true
FORCE_DISABLE_COLLECTION=false
AUTO_EXTRACT_COOKIES=true

# External APIs (사내망 URL로 변경)
REGTECH_BASE_URL=https://regtech.fsec.or.kr
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password

SECUDIUM_BASE_URL=https://isap.secudium.co.kr
SECUDIUM_USERNAME=your-username
SECUDIUM_PASSWORD=your-password

# Logging
LOG_LEVEL=INFO
LOG_FILE=/opt/blacklist/logs/blacklist.log

# Performance
WORKERS=4
WORKER_CONNECTIONS=1000
MAX_REQUESTS=1000
TIMEOUT=30
EOF

# 권한 설정
chmod 600 .env
```

#### 2. Docker Compose 설정
```bash
# RHEL8용 Docker Compose 파일
cat > /opt/blacklist/docker-compose-rhel8.yml << 'EOF'
version: '3.9'

services:
  blacklist:
    image: registry.jclee.me/blacklist:latest
    container_name: blacklist-app
    restart: unless-stopped
    ports:
      - "32542:2542"
    volumes:
      - /opt/blacklist/data:/app/instance
      - /opt/blacklist/logs:/app/logs
      - /opt/blacklist/.env:/app/.env:ro
    environment:
      FLASK_ENV: production
      PORT: 2542
    depends_on:
      - postgresql
      - redis
    networks:
      - blacklist-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2542/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.1'
          memory: 256M

  postgresql:
    image: registry.jclee.me/blacklist-postgresql:latest
    container_name: blacklist-postgresql
    restart: unless-stopped
    ports:
      - "32543:5432"
    volumes:
      - /opt/blacklist/postgresql-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: blacklist
      POSTGRES_USER: blacklist_user
      POSTGRES_PASSWORD: CHANGE_PASSWORD
      PGDATA: /var/lib/postgresql/data/pgdata
    networks:
      - blacklist-net
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "blacklist_user", "-d", "blacklist"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.2'
          memory: 512M

  redis:
    image: registry.jclee.me/blacklist-redis:latest
    container_name: blacklist-redis
    restart: unless-stopped
    volumes:
      - /opt/blacklist/redis-data:/data
    environment:
      REDIS_MAXMEMORY: 512mb
    networks:
      - blacklist-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.1'
          memory: 128M

networks:
  blacklist-net:
    driver: bridge
    name: blacklist-network

volumes:
  postgresql_data:
    driver: local
  redis_data:
    driver: local
EOF
```

### 🚀 서비스 배포

#### 1. 이미지 준비
```bash
# 프라이빗 레지스트리 로그인
echo "REGISTRY_PASSWORD" | docker login registry.jclee.me -u "REGISTRY_USERNAME" --password-stdin

# 이미지 다운로드
docker pull registry.jclee.me/blacklist:latest
docker pull registry.jclee.me/blacklist-postgresql:latest
docker pull registry.jclee.me/blacklist-redis:latest

# 이미지 확인
docker images | grep blacklist
```

#### 2. 데이터베이스 초기화
```bash
# PostgreSQL 컨테이너 먼저 시작
docker compose -f docker-compose-rhel8.yml up -d postgresql

# 데이터베이스 초기화 스크립트 실행
sleep 30  # PostgreSQL 시작 대기
python3 commands/utils/init_database.py --force

# 초기화 확인
python3 commands/utils/init_database.py --check
```

#### 3. 전체 서비스 시작
```bash
# 모든 서비스 시작
docker compose -f docker-compose-rhel8.yml up -d

# 서비스 상태 확인
docker compose -f docker-compose-rhel8.yml ps

# 로그 확인
docker compose -f docker-compose-rhel8.yml logs -f
```

### 🔍 설치 검증

#### 1. 헬스체크
```bash
# 애플리케이션 헬스체크
curl -s http://localhost:32542/health | python3 -m json.tool

# 데이터베이스 연결 확인
curl -s http://localhost:32542/api/health | python3 -m json.tool

# API 엔드포인트 테스트
curl -s http://localhost:32542/api/blacklist/active
```

#### 2. 성능 테스트
```bash
# 부하 테스트 (Apache Bench)
sudo dnf install -y httpd-tools
ab -n 100 -c 10 http://localhost:32542/health

# 메모리 사용량 확인
docker stats --no-stream

# 디스크 사용량 확인
df -h /opt/blacklist
```

### 🔧 시스템 서비스 등록

#### 1. Systemd 서비스 생성
```bash
# Systemd 서비스 파일 생성
sudo cat > /etc/systemd/system/blacklist.service << 'EOF'
[Unit]
Description=Blacklist Management System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=true
WorkingDirectory=/opt/blacklist
ExecStart=/usr/bin/docker compose -f docker-compose-rhel8.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose-rhel8.yml down
TimeoutStartSec=0
User=blacklist
Group=blacklist

[Install]
WantedBy=multi-user.target
EOF

# 서비스 등록 및 활성화
sudo systemctl daemon-reload
sudo systemctl enable blacklist.service
sudo systemctl start blacklist.service

# 서비스 상태 확인
sudo systemctl status blacklist.service
```

#### 2. 자동 시작 설정
```bash
# 부팅시 자동 시작
sudo systemctl enable blacklist.service

# 서비스 재시작 정책
sudo mkdir -p /etc/systemd/system/blacklist.service.d
sudo cat > /etc/systemd/system/blacklist.service.d/restart.conf << 'EOF'
[Service]
Restart=always
RestartSec=10
EOF

sudo systemctl daemon-reload
```

### 📊 모니터링 설정

#### 1. 로그 로테이션
```bash
# logrotate 설정
sudo cat > /etc/logrotate.d/blacklist << 'EOF'
/opt/blacklist/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 blacklist blacklist
    postrotate
        docker restart blacklist-app 2>/dev/null || true
    endscript
}
EOF
```

#### 2. 모니터링 스크립트
```bash
# 헬스체크 스크립트
cat > /opt/blacklist/scripts/health-monitor.sh << 'EOF'
#!/bin/bash
# Blacklist 헬스 모니터링

LOG_FILE="/var/log/blacklist-monitor.log"
ALERT_EMAIL="admin@company.com"

check_health() {
    if ! curl -sf http://localhost:32542/health > /dev/null; then
        echo "[$(date)] CRITICAL: Blacklist service is down" >> $LOG_FILE
        # 이메일 알림 (선택사항)
        # echo "Blacklist service is down on $(hostname)" | mail -s "Blacklist Alert" $ALERT_EMAIL
        return 1
    fi
    return 0
}

check_disk() {
    USAGE=$(df -h /opt/blacklist | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $USAGE -gt 80 ]; then
        echo "[$(date)] WARNING: Disk usage is ${USAGE}%" >> $LOG_FILE
    fi
}

check_memory() {
    MEMORY_USAGE=$(docker stats --no-stream --format "{{.MemPerc}}" blacklist-app | sed 's/%//')
    if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
        echo "[$(date)] WARNING: Memory usage is ${MEMORY_USAGE}%" >> $LOG_FILE
    fi
}

# 실행
check_health
check_disk
check_memory
EOF

chmod +x /opt/blacklist/scripts/health-monitor.sh

# Cron 등록
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/blacklist/scripts/health-monitor.sh") | crontab -
```

### 🔄 백업 및 복구

#### 1. 자동 백업 스크립트
```bash
cat > /opt/blacklist/scripts/backup.sh << 'EOF'
#!/bin/bash
# Blacklist 자동 백업

BACKUP_DIR="/opt/blacklist/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="blacklist_backup_${DATE}"

mkdir -p $BACKUP_DIR

# 데이터베이스 백업
docker exec blacklist-postgresql pg_dump -U blacklist_user blacklist > $BACKUP_DIR/${BACKUP_NAME}_db.sql

# 설정 파일 백업
tar -czf $BACKUP_DIR/${BACKUP_NAME}_config.tar.gz \
    /opt/blacklist/.env \
    /opt/blacklist/docker-compose-rhel8.yml \
    /opt/blacklist/data

# 오래된 백업 삭제 (7일 이상)
find $BACKUP_DIR -name "blacklist_backup_*" -mtime +7 -delete

echo "Backup completed: ${BACKUP_NAME}"
EOF

chmod +x /opt/blacklist/scripts/backup.sh

# 일일 백업 Cron 등록
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/blacklist/scripts/backup.sh") | crontab -
```

#### 2. 복구 스크립트
```bash
cat > /opt/blacklist/scripts/restore.sh << 'EOF'
#!/bin/bash
# Blacklist 복구 스크립트

if [ $# -ne 1 ]; then
    echo "Usage: $0 <backup_date>"
    echo "Example: $0 20250819_020000"
    exit 1
fi

BACKUP_DATE=$1
BACKUP_DIR="/opt/blacklist/backups"

echo "⚠️ WARNING: This will overwrite current data!"
read -p "Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 1
fi

# 서비스 중지
docker compose -f /opt/blacklist/docker-compose-rhel8.yml down

# 데이터베이스 복구
echo "Restoring database..."
docker compose -f /opt/blacklist/docker-compose-rhel8.yml up -d postgresql
sleep 30
docker exec -i blacklist-postgresql psql -U blacklist_user -d blacklist < $BACKUP_DIR/blacklist_backup_${BACKUP_DATE}_db.sql

# 설정 복구
echo "Restoring configuration..."
tar -xzf $BACKUP_DIR/blacklist_backup_${BACKUP_DATE}_config.tar.gz -C /

# 서비스 재시작
docker compose -f /opt/blacklist/docker-compose-rhel8.yml up -d

echo "Restore completed!"
EOF

chmod +x /opt/blacklist/scripts/restore.sh
```

### 📋 최종 체크리스트

#### 설치 완료 확인
- [ ] RHEL8 시스템 업데이트 완료
- [ ] Docker/Podman 설치 및 설정 완료
- [ ] 방화벽 및 SELinux 설정 완료
- [ ] 디렉토리 구조 생성 및 권한 설정 완료
- [ ] 환경변수 설정 완료
- [ ] Docker Compose 설정 완료
- [ ] 데이터베이스 초기화 완료
- [ ] 서비스 시작 및 헬스체크 통과
- [ ] Systemd 서비스 등록 완료
- [ ] 모니터링 및 백업 스크립트 설정 완료

#### 서비스 접속 정보
- **웹 UI**: http://SERVER_IP:32542
- **API 헬스체크**: http://SERVER_IP:32542/health
- **관리자 로그인**: admin / CHANGE_THIS_PASSWORD
- **PostgreSQL**: SERVER_IP:32543
- **로그 위치**: /opt/blacklist/logs/
- **데이터 위치**: /opt/blacklist/data/

#### 운영 명령어
```bash
# 서비스 관리
sudo systemctl start blacklist.service
sudo systemctl stop blacklist.service
sudo systemctl restart blacklist.service
sudo systemctl status blacklist.service

# Docker 관리
docker compose -f /opt/blacklist/docker-compose-rhel8.yml ps
docker compose -f /opt/blacklist/docker-compose-rhel8.yml logs -f
docker compose -f /opt/blacklist/docker-compose-rhel8.yml restart

# 백업/복구
/opt/blacklist/scripts/backup.sh
/opt/blacklist/scripts/restore.sh 20250819_020000

# 모니터링
/opt/blacklist/scripts/health-monitor.sh
tail -f /var/log/blacklist-monitor.log
```

---

**문서 버전**: v1.0.37  
**작성일**: 2025-08-19  
**대상 OS**: Red Hat Enterprise Linux 8.x  
**담당자**: Blacklist System Administrator