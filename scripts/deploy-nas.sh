#!/bin/bash

################################################################################
# Blacklist NAS Deployment Script
# NAS (Synology/QNAP) Docker 환경에 최적화된 배포 스크립트
################################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# NAS 기본 설정
NAS_TYPE="${NAS_TYPE:-synology}"  # synology 또는 qnap
NAS_IP="${NAS_IP:-}"
NAS_USER="${NAS_USER:-admin}"
NAS_DEPLOY_PATH="${NAS_DEPLOY_PATH:-/volume1/docker/blacklist}"

# 함수: 로그 출력
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# 함수: 사용법
usage() {
    cat << EOF
사용법: $0 [옵션]

옵션:
  -n, --nas-ip <IP>           NAS IP 주소
  -u, --user <username>       NAS SSH 사용자명 (기본값: admin)
  -p, --path <path>           NAS 배포 경로 (기본값: /volume1/docker/blacklist)
  -t, --type <type>           NAS 종류: synology 또는 qnap (기본값: synology)
  -l, --local                 로컬에서 패키지 생성만 (SSH 접속 안함)
  -h, --help                  도움말 표시

예제:
  $0 -n 192.168.1.100                    # Synology NAS에 배포
  $0 -n 192.168.1.100 -t qnap            # QNAP NAS에 배포
  $0 -l                                   # 로컬에서 패키지만 생성

EOF
    exit 1
}

# 파라미터 파싱
LOCAL_ONLY=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--nas-ip)
            NAS_IP="$2"
            shift 2
            ;;
        -u|--user)
            NAS_USER="$2"
            shift 2
            ;;
        -p|--path)
            NAS_DEPLOY_PATH="$2"
            shift 2
            ;;
        -t|--type)
            NAS_TYPE="$2"
            shift 2
            ;;
        -l|--local)
            LOCAL_ONLY=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "알 수 없는 옵션: $1"
            usage
            ;;
    esac
done

# 함수: 배포 패키지 생성
create_deployment_package() {
    log "NAS 배포 패키지 생성 중..."
    
    # 임시 디렉토리 생성
    TEMP_DIR=$(mktemp -d)
    PACKAGE_DIR="$TEMP_DIR/blacklist-nas"
    mkdir -p "$PACKAGE_DIR"
    
    # 필요한 파일 복사
    cp docker-compose.yml "$PACKAGE_DIR/"
    cp .env "$PACKAGE_DIR/"
    cp .env.example "$PACKAGE_DIR/"
    
    # NAS용 docker-compose 수정 (볼륨 경로 조정)
    if [ "$NAS_TYPE" = "synology" ]; then
        # Synology 특화 설정
        cat > "$PACKAGE_DIR/docker-compose.nas.yml" << 'EOF'
# Synology NAS용 Docker Compose 설정
version: '3.9'

services:
  blacklist:
    image: registry.jclee.me/blacklist:latest
    container_name: blacklist
    restart: unless-stopped
    ports:
      - "32542:2542"
    volumes:
      - ./data:/app/instance
      - ./logs:/app/logs
    environment:
      FLASK_ENV: production
      PORT: 2542
      DATABASE_URL: "postgresql://blacklist_user:blacklist_password_change_me@postgresql:5432/blacklist"
      REDIS_URL: redis://redis:6379/0
      COLLECTION_ENABLED: "true"
      FORCE_DISABLE_COLLECTION: "false"
    env_file:
      - ./.env
    depends_on:
      - redis
      - postgresql
    networks:
      - blacklist-net

  redis:
    image: registry.jclee.me/blacklist-redis:latest
    container_name: blacklist-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    environment:
      - REDIS_MAXMEMORY=1gb
      - REDIS_MAXMEMORY_POLICY=allkeys-lru
    networks:
      - blacklist-net

  postgresql:
    image: registry.jclee.me/blacklist-postgresql:latest
    container_name: blacklist-postgresql
    restart: unless-stopped
    ports:
      - "32543:5432"
    volumes:
      - postgresql_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: blacklist
      POSTGRES_USER: blacklist_user
      POSTGRES_PASSWORD: blacklist_password_change_me
      PGDATA: /var/lib/postgresql/data/pgdata
    networks:
      - blacklist-net

volumes:
  redis_data:
    driver: local
  postgresql_data:
    driver: local

networks:
  blacklist-net:
    driver: bridge
EOF
    fi
    
    # NAS 배포 스크립트 생성
    cat > "$PACKAGE_DIR/deploy.sh" << 'EOF'
#!/bin/bash
# NAS 배포 실행 스크립트

echo "🚀 Blacklist NAS 배포 시작..."

# Docker Compose 파일 선택
if [ -f docker-compose.nas.yml ]; then
    COMPOSE_FILE="docker-compose.nas.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

# 이미지 풀
echo "📦 Docker 이미지 다운로드 중..."
docker-compose -f $COMPOSE_FILE pull

# 서비스 시작
echo "🔄 서비스 시작 중..."
docker-compose -f $COMPOSE_FILE up -d

# 상태 확인
echo "✅ 배포 상태:"
docker-compose -f $COMPOSE_FILE ps

echo ""
echo "📍 접속 URL: http://$(hostname -I | awk '{print $1}'):32542"
echo "📊 상태 확인: docker-compose -f $COMPOSE_FILE ps"
echo "📜 로그 확인: docker-compose -f $COMPOSE_FILE logs -f"
EOF
    
    chmod +x "$PACKAGE_DIR/deploy.sh"
    
    # 업데이트 스크립트
    cat > "$PACKAGE_DIR/update.sh" << 'EOF'
#!/bin/bash
# NAS 업데이트 스크립트

COMPOSE_FILE="${1:-docker-compose.nas.yml}"

echo "🔄 Blacklist 업데이트 시작..."

# 이미지 풀
docker-compose -f $COMPOSE_FILE pull

# 서비스 재시작
docker-compose -f $COMPOSE_FILE up -d

# 상태 확인
docker-compose -f $COMPOSE_FILE ps

echo "✅ 업데이트 완료"
EOF
    
    chmod +x "$PACKAGE_DIR/update.sh"
    
    # 백업 스크립트
    cat > "$PACKAGE_DIR/backup.sh" << 'EOF'
#!/bin/bash
# NAS 백업 스크립트

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "🔄 백업 시작..."

# PostgreSQL 백업
docker exec blacklist-postgresql pg_dump -U blacklist_user blacklist > $BACKUP_DIR/blacklist_$DATE.sql

# 환경 파일 백업
cp .env $BACKUP_DIR/.env_$DATE

echo "✅ 백업 완료: $BACKUP_DIR"
EOF
    
    chmod +x "$PACKAGE_DIR/backup.sh"
    
    # 패키지 압축
    cd "$TEMP_DIR"
    tar czf blacklist-nas-deploy.tar.gz blacklist-nas/
    mv blacklist-nas-deploy.tar.gz /tmp/
    
    log "✅ 패키지 생성 완료: /tmp/blacklist-nas-deploy.tar.gz"
    
    # 정리
    rm -rf "$TEMP_DIR"
    
    echo "$PACKAGE_DIR"
}

# 함수: SSH로 NAS에 배포
deploy_to_nas() {
    log "NAS에 배포 중: $NAS_USER@$NAS_IP"
    
    # SSH 연결 테스트
    if ! ssh -o ConnectTimeout=5 "$NAS_USER@$NAS_IP" "echo 'SSH 연결 성공'" &>/dev/null; then
        error "SSH 연결 실패. SSH 설정을 확인해주세요."
        info "Synology: 제어판 > 터미널 및 SNMP > SSH 서비스 활성화"
        info "QNAP: 제어판 > 네트워크 서비스 > SSH 활성화"
        exit 1
    fi
    
    # NAS에 디렉토리 생성
    ssh "$NAS_USER@$NAS_IP" "mkdir -p $NAS_DEPLOY_PATH"
    
    # 패키지 전송
    log "패키지 전송 중..."
    scp /tmp/blacklist-nas-deploy.tar.gz "$NAS_USER@$NAS_IP:$NAS_DEPLOY_PATH/"
    
    # NAS에서 패키지 압축 해제 및 배포
    log "NAS에서 배포 실행 중..."
    ssh "$NAS_USER@$NAS_IP" << EOF
cd $NAS_DEPLOY_PATH
tar xzf blacklist-nas-deploy.tar.gz
cd blacklist-nas
./deploy.sh
EOF
    
    log "✅ NAS 배포 완료"
}

# 함수: Synology DSM 웹 UI 설정 안내
show_synology_guide() {
    cat << EOF

================================================
   Synology DSM 설정 가이드
================================================

1. DSM 웹 인터페이스 접속
   - http://$NAS_IP:5000 (DSM 6)
   - http://$NAS_IP:5001 (DSM 7)

2. Docker 패키지 설치
   - 패키지 센터 > Docker 검색 및 설치

3. Container Manager (DSM 7) / Docker (DSM 6)
   - 컨테이너 목록에서 blacklist 확인
   - 포트 매핑 확인: 32542

4. 방화벽 설정
   - 제어판 > 보안 > 방화벽
   - 포트 32542 허용 규칙 추가

5. 리소스 모니터링
   - 리소스 모니터 > Docker 탭

EOF
}

# 함수: QNAP Container Station 설정 안내
show_qnap_guide() {
    cat << EOF

================================================
   QNAP Container Station 설정 가이드
================================================

1. QNAP 웹 인터페이스 접속
   - http://$NAS_IP:8080

2. Container Station 설치
   - App Center > Container Station 설치

3. Container Station 열기
   - 컨테이너 목록에서 blacklist 확인
   - 네트워크 설정 확인

4. 방화벽 설정
   - 제어판 > 보안 > 방화벽
   - 포트 32542 허용

5. 리소스 모니터링
   - Container Station > 개요

EOF
}

# 메인 실행
main() {
    echo "================================================"
    echo "   Blacklist NAS Deployment Script v1.0"
    echo "================================================"
    echo ""
    
    # 패키지 생성
    create_deployment_package
    
    if [ "$LOCAL_ONLY" = true ]; then
        echo ""
        echo "📦 패키지 생성 완료: /tmp/blacklist-nas-deploy.tar.gz"
        echo ""
        echo "수동 배포 방법:"
        echo "1. 패키지를 NAS로 전송"
        echo "2. SSH로 NAS 접속"
        echo "3. tar xzf blacklist-nas-deploy.tar.gz"
        echo "4. cd blacklist-nas && ./deploy.sh"
    else
        # NAS IP 확인
        if [ -z "$NAS_IP" ]; then
            error "NAS IP 주소를 지정해주세요 (-n 옵션)"
            usage
        fi
        
        # NAS에 배포
        deploy_to_nas
        
        # NAS 종류별 가이드 표시
        if [ "$NAS_TYPE" = "synology" ]; then
            show_synology_guide
        elif [ "$NAS_TYPE" = "qnap" ]; then
            show_qnap_guide
        fi
    fi
    
    echo ""
    echo "================================================"
    echo "   ✅ 완료!"
    echo "================================================"
    echo ""
    echo "📍 접속 URL: http://$NAS_IP:32542"
    echo "📁 배포 경로: $NAS_DEPLOY_PATH"
    echo ""
    echo "🔧 유용한 명령어:"
    echo "  - SSH 접속: ssh $NAS_USER@$NAS_IP"
    echo "  - 상태 확인: docker ps | grep blacklist"
    echo "  - 업데이트: cd $NAS_DEPLOY_PATH/blacklist-nas && ./update.sh"
    echo "  - 백업: cd $NAS_DEPLOY_PATH/blacklist-nas && ./backup.sh"
    echo ""
}

# 스크립트 실행
main "$@"