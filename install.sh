#!/bin/bash

################################################################################
# Blacklist Installation Script
# 원격 서버에서 직접 실행하는 설치 스크립트
# 
# 사용법:
#   curl -fsSL https://raw.githubusercontent.com/JCLEE94/blacklist/main/install.sh | bash
#   또는
#   wget -qO- https://raw.githubusercontent.com/JCLEE94/blacklist/main/install.sh | bash
################################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 기본 설정
INSTALL_DIR="${INSTALL_DIR:-/opt/blacklist}"
GITHUB_REPO="https://github.com/JCLEE94/blacklist"
GITHUB_RAW="https://raw.githubusercontent.com/JCLEE94/blacklist/main"
REGISTRY_URL="registry.jclee.me"
COMPOSE_CMD=""

# 함수: 로그 출력
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${CYAN}✅${NC} $1"
}

# 함수: 배너 표시
show_banner() {
    cat << 'EOF'
 ____  _            _    _ _     _   
| __ )| | __ _  ___| | _| (_)___| |_ 
|  _ \| |/ _` |/ __| |/ / | / __| __|
| |_) | | (_| | (__|   <| | \__ \ |_ 
|____/|_|\__,_|\___|_|\_\_|_|___/\__|
                                      
    Blacklist Management System v1.0
    Automated Installation Script
EOF
    echo ""
}

# 함수: 시스템 요구사항 확인
check_requirements() {
    log "시스템 요구사항 확인 중..."
    
    # OS 확인
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
        info "OS: $OS $VER"
    fi
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        warning "Docker가 설치되어 있지 않습니다. 설치를 시작합니다..."
        install_docker
    else
        success "Docker 설치됨: $(docker --version)"
    fi
    
    # Docker Compose 확인
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        success "Docker Compose V1 설치됨: $(docker-compose --version)"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        success "Docker Compose V2 설치됨: $(docker compose version)"
    else
        warning "Docker Compose가 없습니다. 설치를 시작합니다..."
        install_docker_compose
    fi
    
    # curl 또는 wget 확인
    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        info "curl 설치 중..."
        if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
            sudo apt-get update && sudo apt-get install -y curl
        elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "rocky" ]; then
            sudo yum install -y curl
        fi
    fi
    
    # Git 확인 (선택사항)
    if command -v git &> /dev/null; then
        success "Git 설치됨"
        USE_GIT=true
    else
        info "Git이 없습니다. wget/curl을 사용합니다."
        USE_GIT=false
    fi
}

# 함수: Docker 설치
install_docker() {
    log "Docker 설치 중..."
    
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        # Ubuntu/Debian
        curl -fsSL https://get.docker.com | sudo sh
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "rocky" ]; then
        # RHEL/CentOS/Rocky
        sudo yum install -y yum-utils
        sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo yum install -y docker-ce docker-ce-cli containerd.io
    else
        error "지원하지 않는 OS입니다. Docker를 수동으로 설치해주세요."
    fi
    
    # Docker 서비스 시작
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # 현재 사용자를 docker 그룹에 추가
    sudo usermod -aG docker $USER
    
    success "Docker 설치 완료"
}

# 함수: Docker Compose 설치
install_docker_compose() {
    log "Docker Compose 설치 중..."
    
    # Docker Compose V2 설치 (플러그인 방식)
    DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
    mkdir -p $DOCKER_CONFIG/cli-plugins
    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
    chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
    
    COMPOSE_CMD="docker compose"
    success "Docker Compose V2 설치 완료"
}

# 함수: 디렉토리 준비
prepare_directories() {
    log "설치 디렉토리 준비 중..."
    
    # 설치 디렉토리 생성
    sudo mkdir -p $INSTALL_DIR
    sudo chown $USER:$USER $INSTALL_DIR
    cd $INSTALL_DIR
    
    # 필요한 서브 디렉토리 생성
    mkdir -p data logs postgresql-data redis-data backups
    
    success "디렉토리 준비 완료: $INSTALL_DIR"
}

# 함수: 파일 다운로드
download_files() {
    log "필요한 파일 다운로드 중..."
    
    if [ "$USE_GIT" = true ]; then
        # Git clone 사용
        log "Git을 사용하여 저장소 클론..."
        git clone $GITHUB_REPO temp_repo
        cp temp_repo/docker-compose.yml ./
        cp temp_repo/.env.example ./
        cp temp_repo/.env ./ 2>/dev/null || cp .env.example .env
        rm -rf temp_repo
    else
        # wget/curl 사용
        log "파일 직접 다운로드..."
        if command -v curl &> /dev/null; then
            curl -fsSL $GITHUB_RAW/docker-compose.yml -o docker-compose.yml
            curl -fsSL $GITHUB_RAW/.env.example -o .env.example
            curl -fsSL $GITHUB_RAW/.env -o .env 2>/dev/null || cp .env.example .env
        else
            wget -q $GITHUB_RAW/docker-compose.yml -O docker-compose.yml
            wget -q $GITHUB_RAW/.env.example -O .env.example
            wget -q $GITHUB_RAW/.env -O .env 2>/dev/null || cp .env.example .env
        fi
    fi
    
    success "파일 다운로드 완료"
}

# 함수: 환경 설정
configure_environment() {
    log "환경 설정 중..."
    
    # .env 파일 확인
    if [ ! -f .env ]; then
        cp .env.example .env
    fi
    
    # 중요 설정 확인
    echo ""
    warning "환경 변수 설정이 필요합니다!"
    echo ""
    echo "다음 항목을 설정해주세요 (.env 파일):"
    echo "  1. REGTECH_USERNAME, REGTECH_PASSWORD"
    echo "  2. SECUDIUM_USERNAME, SECUDIUM_PASSWORD"
    echo "  3. DATABASE 비밀번호 (선택사항)"
    echo "  4. SECRET_KEY, JWT_SECRET_KEY (선택사항)"
    echo ""
    read -p "지금 .env 파일을 수정하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-vi} .env
    else
        warning ".env 파일을 나중에 수정해주세요: $INSTALL_DIR/.env"
    fi
}

# 함수: 레지스트리 로그인
registry_login() {
    log "Docker 레지스트리 설정 중..."
    
    echo ""
    info "registry.jclee.me 레지스트리 로그인이 필요합니다."
    echo "GitHub Container Registry 토큰이 필요합니다."
    echo ""
    read -p "레지스트리에 로그인하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "사용자명: " REGISTRY_USERNAME
        read -sp "비밀번호/토큰: " REGISTRY_PASSWORD
        echo
        
        echo $REGISTRY_PASSWORD | docker login $REGISTRY_URL -u $REGISTRY_USERNAME --password-stdin
        
        if [ $? -eq 0 ]; then
            success "레지스트리 로그인 성공"
        else
            error "레지스트리 로그인 실패"
        fi
    else
        warning "레지스트리 로그인을 건너뜁니다. 나중에 수동으로 로그인해주세요."
    fi
}

# 함수: 서비스 시작
start_services() {
    log "Docker 서비스 시작 중..."
    
    # 이미지 풀
    log "Docker 이미지 다운로드 중... (시간이 걸릴 수 있습니다)"
    $COMPOSE_CMD pull
    
    # 서비스 시작
    $COMPOSE_CMD up -d
    
    if [ $? -eq 0 ]; then
        success "서비스 시작 완료"
    else
        error "서비스 시작 실패"
    fi
}

# 함수: 헬스체크
health_check() {
    log "서비스 헬스체크 중..."
    
    local max_attempts=30
    local attempt=0
    
    echo -n "서비스가 준비될 때까지 대기 중"
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf http://localhost:32542/health > /dev/null 2>&1; then
            echo ""
            success "헬스체크 성공!"
            echo ""
            curl -s http://localhost:32542/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:32542/health
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    echo ""
    warning "헬스체크 타임아웃 (${max_attempts}초)"
    return 1
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
WorkingDirectory=$INSTALL_DIR
ExecStart=$COMPOSE_CMD up -d
ExecStop=$COMPOSE_CMD down
ExecReload=$COMPOSE_CMD pull && $COMPOSE_CMD up -d
StandardOutput=journal
User=$USER

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable blacklist.service
    
    success "systemd 서비스 생성 완료"
}

# 함수: 스크립트 생성
create_scripts() {
    log "관리 스크립트 생성 중..."
    
    # 업데이트 스크립트
    cat << 'EOF' > update.sh
#!/bin/bash
# Blacklist 업데이트 스크립트

cd $(dirname $0)

echo "🔄 Blacklist 업데이트 시작..."

# 최신 docker-compose.yml 다운로드
curl -fsSL https://raw.githubusercontent.com/JCLEE94/blacklist/main/docker-compose.yml -o docker-compose.yml.new

if [ -f docker-compose.yml.new ]; then
    mv docker-compose.yml docker-compose.yml.backup
    mv docker-compose.yml.new docker-compose.yml
fi

# 이미지 풀
docker-compose pull

# 서비스 재시작
docker-compose up -d

# 상태 확인
docker-compose ps

echo "✅ 업데이트 완료"
EOF
    chmod +x update.sh
    
    # 백업 스크립트
    cat << 'EOF' > backup.sh
#!/bin/bash
# Blacklist 백업 스크립트

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "🔄 백업 시작..."

# PostgreSQL 백업
docker exec blacklist-postgresql pg_dump -U blacklist_user blacklist > $BACKUP_DIR/blacklist_$DATE.sql

# 환경 파일 백업
cp .env $BACKUP_DIR/.env_$DATE

# 오래된 백업 삭제 (7일 이상)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name ".env_*" -mtime +7 -delete

echo "✅ 백업 완료: $BACKUP_DIR"
EOF
    chmod +x backup.sh
    
    # 상태 확인 스크립트
    cat << 'EOF' > status.sh
#!/bin/bash
# Blacklist 상태 확인

echo "📊 Blacklist 서비스 상태"
echo "========================"
docker-compose ps
echo ""
echo "📈 리소스 사용량:"
docker stats --no-stream blacklist blacklist-postgresql blacklist-redis
echo ""
echo "🔍 헬스체크:"
curl -s http://localhost:32542/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:32542/health
EOF
    chmod +x status.sh
    
    success "관리 스크립트 생성 완료"
}

# 함수: 방화벽 설정
configure_firewall() {
    log "방화벽 설정 중..."
    
    # firewalld (RHEL/CentOS/Rocky)
    if command -v firewall-cmd &> /dev/null; then
        sudo firewall-cmd --add-port=32542/tcp --permanent
        sudo firewall-cmd --reload
        success "firewalld 포트 32542 오픈"
    # ufw (Ubuntu/Debian)
    elif command -v ufw &> /dev/null; then
        sudo ufw allow 32542/tcp
        success "ufw 포트 32542 오픈"
    else
        info "방화벽을 수동으로 설정해주세요 (포트: 32542)"
    fi
}

# 함수: 설치 완료 메시지
show_completion_message() {
    local ip=$(hostname -I | awk '{print $1}')
    
    cat << EOF

================================================
   ✅ Blacklist 설치 완료!
================================================

📍 접속 URL: http://$ip:32542
📁 설치 경로: $INSTALL_DIR
📝 로그 파일: $INSTALL_DIR/logs/

🔧 유용한 명령어:
  - 상태 확인: cd $INSTALL_DIR && ./status.sh
  - 로그 확인: cd $INSTALL_DIR && $COMPOSE_CMD logs -f
  - 업데이트: cd $INSTALL_DIR && ./update.sh
  - 백업: cd $INSTALL_DIR && ./backup.sh
  - 서비스 재시작: systemctl restart blacklist
  - 서비스 중지: cd $INSTALL_DIR && $COMPOSE_CMD down
  - 서비스 시작: cd $INSTALL_DIR && $COMPOSE_CMD up -d

⚠️  중요: .env 파일에서 필수 설정을 확인하세요!
  $INSTALL_DIR/.env

📚 문서: https://github.com/JCLEE94/blacklist

================================================

EOF
}

# 메인 실행
main() {
    clear
    show_banner
    
    log "Blacklist 설치를 시작합니다..."
    echo ""
    
    # 설치 디렉토리 확인
    read -p "설치 경로 [$INSTALL_DIR]: " custom_dir
    if [ ! -z "$custom_dir" ]; then
        INSTALL_DIR="$custom_dir"
    fi
    
    # 단계별 실행
    check_requirements
    prepare_directories
    download_files
    configure_environment
    registry_login
    start_services
    health_check
    create_systemd_service
    create_scripts
    configure_firewall
    
    # 완료 메시지
    show_completion_message
}

# 스크립트 실행
main "$@"