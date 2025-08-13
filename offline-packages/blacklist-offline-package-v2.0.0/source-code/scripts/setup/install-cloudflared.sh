#!/bin/bash
# Cloudflare Tunnel 설치 및 설정 스크립트

echo "🌐 Cloudflare Tunnel (cloudflared) 설치 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 시스템 확인
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        print_error "운영체제를 확인할 수 없습니다."
        exit 1
    fi
}

# Cloudflared 설치 함수
install_cloudflared() {
    print_step "Cloudflared 설치 중..."
    
    if command -v cloudflared &> /dev/null; then
        print_warning "Cloudflared가 이미 설치되어 있습니다."
        cloudflared --version
        return 0
    fi
    
    detect_os
    
    case "$OS" in
        "Ubuntu"|"Debian GNU/Linux")
            # Add cloudflare gpg key
            print_step "Cloudflare GPG 키 추가 중..."
            sudo mkdir -p --mode=0755 /usr/share/keyrings
            curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
            
            # Add this repo to your apt repositories
            print_step "Cloudflare 저장소 추가 중..."
            echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
            
            # install cloudflared
            print_step "cloudflared 패키지 설치 중..."
            sudo apt-get update && sudo apt-get install -y cloudflared
            ;;
            
        "CentOS Linux"|"Red Hat Enterprise Linux"|"Rocky Linux")
            print_step "RPM 기반 시스템에서 설치 중..."
            curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.rpm -o cloudflared.rpm
            sudo rpm -i cloudflared.rpm
            rm cloudflared.rpm
            ;;
            
        *)
            print_warning "자동 설치가 지원되지 않는 OS입니다. 바이너리를 직접 다운로드합니다..."
            curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
            chmod +x cloudflared
            sudo mv cloudflared /usr/local/bin/
            ;;
    esac
    
    # 설치 확인
    if command -v cloudflared &> /dev/null; then
        print_success "Cloudflared 설치 완료!"
        cloudflared --version
    else
        print_error "Cloudflared 설치 실패!"
        return 1
    fi
}

# Cloudflare Tunnel 설정 함수
setup_tunnel() {
    print_step "Cloudflare Tunnel 설정 중..."
    
    # 환경 변수 확인
    if [[ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]]; then
        print_warning "CLOUDFLARE_TUNNEL_TOKEN 환경 변수가 설정되지 않았습니다."
        echo "Cloudflare Zero Trust 대시보드에서 터널을 생성하고 토큰을 받아주세요."
        echo "https://one.dash.cloudflare.com/"
        echo ""
        echo "터널 토큰을 입력하세요:"
        read -r CLOUDFLARE_TUNNEL_TOKEN
    fi
    
    if [[ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]]; then
        print_error "터널 토큰이 필요합니다."
        return 1
    fi
    
    # systemd 서비스 생성
    print_step "systemd 서비스 생성 중..."
    sudo tee /etc/systemd/system/cloudflared-blacklist.service > /dev/null <<EOF
[Unit]
Description=Cloudflare Tunnel for Blacklist Service
After=network.target

[Service]
Type=simple
User=cloudflared
Group=cloudflared
ExecStart=/usr/bin/cloudflared tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # cloudflared 사용자 생성 (필요한 경우)
    if ! id -u cloudflared &>/dev/null; then
        print_step "cloudflared 사용자 생성 중..."
        sudo useradd -r -s /bin/false cloudflared
    fi
    
    # 서비스 시작
    print_step "서비스 시작 중..."
    sudo systemctl daemon-reload
    sudo systemctl enable cloudflared-blacklist.service
    sudo systemctl start cloudflared-blacklist.service
    
    # 상태 확인
    if sudo systemctl is-active --quiet cloudflared-blacklist.service; then
        print_success "Cloudflare Tunnel 서비스가 성공적으로 시작되었습니다!"
        sudo systemctl status cloudflared-blacklist.service --no-pager
    else
        print_error "서비스 시작 실패!"
        sudo journalctl -u cloudflared-blacklist.service -n 20 --no-pager
        return 1
    fi
}

# NodePort를 통한 로컬 서비스 연결 설정
configure_nodeport_tunnel() {
    local NODE_PORT="${1:-32452}"
    local SERVICE_URL="${2:-http://localhost:$NODE_PORT}"
    
    print_step "NodePort 서비스($NODE_PORT)에 대한 터널 설정 중..."
    
    # 설정 파일 생성
    sudo mkdir -p /etc/cloudflared
    sudo tee /etc/cloudflared/blacklist-config.yml > /dev/null <<EOF
tunnel: blacklist-tunnel
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: blacklist.yourdomain.com
    service: $SERVICE_URL
  - service: http_status:404
EOF
    
    print_success "NodePort 터널 설정 완료!"
    echo "설정된 서비스 URL: $SERVICE_URL"
}

# 메인 실행
main() {
    echo "======================================"
    echo "Cloudflare Tunnel 설치 및 설정 스크립트"
    echo "======================================"
    echo ""
    
    # 명령어 파싱
    case "${1:-install}" in
        install)
            install_cloudflared
            ;;
        setup)
            setup_tunnel
            ;;
        configure-nodeport)
            configure_nodeport_tunnel "${2:-32452}" "${3}"
            ;;
        all)
            install_cloudflared && setup_tunnel && configure_nodeport_tunnel
            ;;
        *)
            echo "사용법: $0 [install|setup|configure-nodeport|all] [nodeport] [service-url]"
            echo ""
            echo "명령어:"
            echo "  install           - cloudflared 설치만 수행"
            echo "  setup             - 터널 설정 및 서비스 시작"
            echo "  configure-nodeport - NodePort 서비스에 대한 터널 설정"
            echo "  all               - 모든 작업 수행"
            echo ""
            echo "예시:"
            echo "  $0 install"
            echo "  $0 setup"
            echo "  $0 configure-nodeport 32452"
            echo "  $0 all"
            exit 1
            ;;
    esac
}

main "$@"