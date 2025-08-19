#!/bin/bash

################################################################################
# Blacklist Remote Deployment Script
# 원격 서버에 Docker Compose 기반 애플리케이션 배포
################################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 기본 설정
DEPLOY_DIR="/opt/blacklist"
REGISTRY_URL="registry.jclee.me"
SOURCE_SERVER="${SOURCE_SERVER:-}"  # 소스 서버 주소 (예: user@server.com:/path)

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
  -s, --source <server:path>   소스 서버 경로 (예: user@192.168.1.100:/home/jclee/app/blacklist)
  -d, --deploy-dir <path>      배포 디렉토리 (기본값: /opt/blacklist)
  -h, --help                   도움말 표시

예제:
  $0 -s jclee@192.168.1.100:/home/jclee/app/blacklist
  $0 --source user@server.com:/app/blacklist --deploy-dir /var/app/blacklist

EOF
    exit 1
}

# 파라미터 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--source)
            SOURCE_SERVER="$2"
            shift 2
            ;;
        -d|--deploy-dir)
            DEPLOY_DIR="$2"
            shift 2
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

# 소스 서버 확인
if [ -z "$SOURCE_SERVER" ]; then
    error "소스 서버를 지정해주세요 (-s 옵션)"
    usage
fi

# 함수: 시스템 요구사항 확인
check_requirements() {
    log "시스템 요구사항 확인 중..."
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        error "Docker가 설치되어 있지 않습니다."
        info "Docker 설치: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    
    # Docker Compose 확인
    if ! command -v docker-compose &> /dev/null; then
        if docker compose version &> /dev/null; then
            info "Docker Compose V2 사용"
            COMPOSE_CMD="docker compose"
        else
            error "Docker Compose가 설치되어 있지 않습니다."
            exit 1
        fi
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    # scp/rsync 확인
    if ! command -v scp &> /dev/null && ! command -v rsync &> /dev/null; then
        error "scp 또는 rsync가 필요합니다."
        exit 1
    fi
    
    log "✅ 모든 요구사항 충족"
}

# 함수: 디렉토리 준비
prepare_directories() {
    log "배포 디렉토리 준비 중..."
    
    # 배포 디렉토리 생성
    sudo mkdir -p $DEPLOY_DIR
    sudo chown $USER:$USER $DEPLOY_DIR
    cd $DEPLOY_DIR
    
    # 필요한 서브 디렉토리 생성
    mkdir -p data logs postgresql-data redis-data postgresql-init
    
    log "✅ 디렉토리 준비 완료: $DEPLOY_DIR"
}

# 함수: 소스 서버에서 파일 가져오기
fetch_files_from_source() {
    log "소스 서버에서 파일 가져오는 중: $SOURCE_SERVER"
    
    # 기존 파일 백업
    if [ -f docker-compose.yml ]; then
        cp docker-compose.yml docker-compose.yml.$(date +%Y%m%d_%H%M%S)
        info "기존 docker-compose.yml 백업됨"
    fi
    
    if [ -f .env ]; then
        cp .env .env.$(date +%Y%m%d_%H%M%S)
        info "기존 .env 백업됨"
    fi
    
    # rsync 사용 (우선)
    if command -v rsync &> /dev/null; then
        log "rsync로 파일 동기화 중..."
        rsync -avz --progress \
            --include="docker-compose.yml" \
            --include=".env" \
            --include=".env.example" \
            --exclude="*" \
            "$SOURCE_SERVER/" ./
        
        # docker 디렉토리도 가져오기 (필요한 경우)
        if ssh ${SOURCE_SERVER%%:*} "test -d ${SOURCE_SERVER#*:}/docker" 2>/dev/null; then
            rsync -avz --progress "$SOURCE_SERVER/docker/" ./docker/
        fi
    else
        # scp 사용
        log "scp로 파일 복사 중..."
        scp "$SOURCE_SERVER/docker-compose.yml" ./
        scp "$SOURCE_SERVER/.env" ./
        scp "$SOURCE_SERVER/.env.example" ./ 2>/dev/null || true
        
        # docker 디렉토리 복사 (필요한 경우)
        if ssh ${SOURCE_SERVER%%:*} "test -d ${SOURCE_SERVER#*:}/docker" 2>/dev/null; then
            scp -r "$SOURCE_SERVER/docker" ./
        fi
    fi
    
    log "✅ 파일 가져오기 완료"
}

# 함수: 환경 변수 확인
check_environment() {
    log "환경 변수 확인 중..."
    
    if [ ! -f .env ]; then
        error ".env 파일이 없습니다!"
        if [ -f .env.example ]; then
            cp .env.example .env
            warning ".env.example을 복사했습니다. 수정이 필요합니다."
        fi
        exit 1
    fi
    
    # 중요 환경변수 확인
    local missing_vars=()
    
    # .env 파일에서 필수 변수 확인
    for var in REGTECH_USERNAME REGTECH_PASSWORD DATABASE_URL; do
        if ! grep -q "^$var=" .env; then
            missing_vars+=($var)
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        warning "다음 환경 변수가 설정되지 않았습니다: ${missing_vars[*]}"
        read -p ".env 파일을 수정하시겠습니까? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-vi} .env
        fi
    else
        log "✅ 환경 변수 설정 확인 완료"
    fi
}

# 함수: 레지스트리 로그인
registry_login() {
    log "레지스트리 로그인 중..."
    
    # .env에서 레지스트리 정보 읽기
    if [ -f .env ]; then
        source .env
    fi
    
    if [ -z "$REGISTRY_USERNAME" ] || [ -z "$REGISTRY_PASSWORD" ]; then
        warning "레지스트리 자격증명이 설정되지 않았습니다."
        read -p "레지스트리 사용자명: " REGISTRY_USERNAME
        read -sp "레지스트리 비밀번호: " REGISTRY_PASSWORD
        echo
    fi
    
    echo $REGISTRY_PASSWORD | docker login $REGISTRY_URL -u $REGISTRY_USERNAME --password-stdin
    
    if [ $? -eq 0 ]; then
        log "✅ 레지스트리 로그인 성공"
    else
        error "레지스트리 로그인 실패"
        exit 1
    fi
}

# 함수: 이미지 풀
pull_images() {
    log "Docker 이미지 풀 중..."
    
    $COMPOSE_CMD pull
    
    log "✅ 이미지 풀 완료"
}

# 함수: 서비스 시작
start_services() {
    log "서비스 시작 중..."
    
    $COMPOSE_CMD up -d
    
    if [ $? -eq 0 ]; then
        log "✅ 서비스 시작 완료"
    else
        error "서비스 시작 실패"
        exit 1
    fi
}

# 함수: 헬스체크
health_check() {
    log "헬스체크 수행 중..."
    
    # 30초 대기
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf http://localhost:32542/health > /dev/null 2>&1; then
            log "✅ 헬스체크 성공"
            curl -s http://localhost:32542/health | jq '.' 2>/dev/null || curl -s http://localhost:32542/health
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    echo
    error "헬스체크 실패 (${max_attempts}초 타임아웃)"
    return 1
}

# 함수: 서비스 상태 확인
check_status() {
    log "서비스 상태:"
    $COMPOSE_CMD ps
}

# 함수: 업데이트 스크립트 생성
create_update_script() {
    log "업데이트 스크립트 생성 중..."
    
    cat << EOF > update.sh
#!/bin/bash
# Blacklist 업데이트 스크립트
# 소스: $SOURCE_SERVER

cd \$(dirname \$0)

echo "🔄 Blacklist 업데이트 시작..."

# 최신 파일 가져오기
if command -v rsync &> /dev/null; then
    rsync -avz --progress \\
        --include="docker-compose.yml" \\
        --include=".env.example" \\
        --exclude=".env" \\
        --exclude="*" \\
        "$SOURCE_SERVER/" ./
else
    scp "$SOURCE_SERVER/docker-compose.yml" ./
fi

# 이미지 풀
$COMPOSE_CMD pull

# 서비스 재시작
$COMPOSE_CMD up -d

# 상태 확인
$COMPOSE_CMD ps

echo "✅ 업데이트 완료"
EOF

    chmod +x update.sh
    log "✅ 업데이트 스크립트 생성: ./update.sh"
}

# 함수: 백업 스크립트 생성
create_backup_script() {
    log "백업 스크립트 생성 중..."
    
    cat << EOF > backup.sh
#!/bin/bash
# Blacklist 백업 스크립트

BACKUP_DIR="/backup/blacklist"
DATE=\$(date +%Y%m%d_%H%M%S)

mkdir -p \$BACKUP_DIR

echo "🔄 백업 시작..."

# PostgreSQL 백업
docker exec blacklist-postgresql pg_dump -U blacklist_user blacklist > \$BACKUP_DIR/blacklist_\$DATE.sql

# 환경 파일 백업
cp .env \$BACKUP_DIR/.env_\$DATE
cp docker-compose.yml \$BACKUP_DIR/docker-compose.yml_\$DATE

# 오래된 백업 삭제 (7일 이상)
find \$BACKUP_DIR -name "*.sql" -mtime +7 -delete
find \$BACKUP_DIR -name ".env_*" -mtime +7 -delete

echo "✅ 백업 완료: \$BACKUP_DIR"
EOF

    chmod +x backup.sh
    log "✅ 백업 스크립트 생성: ./backup.sh"
}

# 함수: systemd 서비스 생성
create_systemd_service() {
    log "systemd 서비스 생성 중..."
    
    cat << EOF | sudo tee /etc/systemd/system/blacklist.service > /dev/null
[Unit]
Description=Blacklist Management System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DEPLOY_DIR
ExecStart=$COMPOSE_CMD up -d
ExecStop=$COMPOSE_CMD down
ExecReload=$COMPOSE_CMD pull && $COMPOSE_CMD up -d
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable blacklist.service
    log "✅ systemd 서비스 생성 완료"
}

# 메인 실행
main() {
    echo "================================================"
    echo "   Blacklist Remote Deployment Script v1.0"
    echo "================================================"
    echo ""
    echo "📍 소스 서버: $SOURCE_SERVER"
    echo "📁 배포 경로: $DEPLOY_DIR"
    echo ""
    
    # 단계별 실행
    check_requirements
    prepare_directories
    fetch_files_from_source
    check_environment
    registry_login
    pull_images
    start_services
    health_check
    check_status
    create_update_script
    create_backup_script
    create_systemd_service
    
    echo ""
    echo "================================================"
    echo "   ✅ 배포 완료!"
    echo "================================================"
    echo ""
    echo "📍 접속 URL: http://$(hostname -I | awk '{print $1}'):32542"
    echo "📁 배포 경로: $DEPLOY_DIR"
    echo ""
    echo "🔧 유용한 명령어:"
    echo "  - 상태 확인: $COMPOSE_CMD ps"
    echo "  - 로그 확인: $COMPOSE_CMD logs -f"
    echo "  - 업데이트: ./update.sh"
    echo "  - 백업: ./backup.sh"
    echo "  - 서비스 재시작: systemctl restart blacklist"
    echo ""
}

# 스크립트 실행
main "$@"