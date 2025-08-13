#!/bin/bash

echo "🔧 원격 서버 SSH 설정 스크립트"
echo "================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 원격 서버 정보
REMOTE_HOST="192.168.50.110"
REMOTE_USER="jclee"
REMOTE_PASSWORD="bingogo1"

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# SSH 키 생성 및 배포
setup_ssh_keys() {
    print_step "SSH 키 설정 중..."
    
    # SSH 키가 없으면 생성
    if [ ! -f ~/.ssh/id_rsa ]; then
        print_step "SSH 키 생성 중..."
        ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
        print_success "SSH 키 생성 완료"
    fi
    
    # sshpass 설치 확인
    if ! command -v sshpass &> /dev/null; then
        print_step "sshpass 설치 중..."
        sudo apt-get update -qq
        sudo apt-get install -y sshpass
    fi
    
    # SSH 키 복사
    print_step "원격 서버에 SSH 키 복사 중..."
    sshpass -p "$REMOTE_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST"
    
    # SSH 연결 테스트
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "echo 'SSH 연결 성공'" &> /dev/null; then
        print_success "SSH 키 설정 완료"
    else
        print_error "SSH 연결 실패"
        exit 1
    fi
}

# 원격 서버에 필요한 도구 설치
install_remote_tools() {
    print_step "원격 서버에 필요한 도구 설치 중..."
    
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
# 패키지 업데이트
sudo apt-get update -qq

# Docker 설치 (이미 설치되어 있으면 스킵)
if ! command -v docker &> /dev/null; then
    echo "Docker 설치 중..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

# kubectl 설치
if ! command -v kubectl &> /dev/null; then
    echo "kubectl 설치 중..."
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl
fi

# ArgoCD CLI 설치
if ! command -v argocd &> /dev/null; then
    echo "ArgoCD CLI 설치 중..."
    curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
    sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
    rm argocd-linux-amd64
fi

# Git 설치
if ! command -v git &> /dev/null; then
    echo "Git 설치 중..."
    sudo apt-get install -y git
fi

echo "도구 설치 완료"
EOF
    
    print_success "원격 서버 도구 설치 완료"
}

# Kubernetes 설정 파일 복사
copy_k8s_config() {
    print_step "Kubernetes 설정 파일 복사 중..."
    
    # 로컬 kubeconfig가 있는지 확인
    if [ ! -f ~/.kube/config ]; then
        print_error "로컬에 Kubernetes 설정 파일이 없습니다."
        exit 1
    fi
    
    # 원격 서버에 .kube 디렉토리 생성
    ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p ~/.kube"
    
    # kubeconfig 복사
    scp ~/.kube/config "$REMOTE_USER@$REMOTE_HOST:~/.kube/config"
    
    # 권한 설정
    ssh "$REMOTE_USER@$REMOTE_HOST" "chmod 600 ~/.kube/config"
    
    # 연결 테스트
    if ssh "$REMOTE_USER@$REMOTE_HOST" "kubectl cluster-info" &> /dev/null; then
        print_success "Kubernetes 설정 복사 완료"
    else
        print_error "Kubernetes 연결 실패"
        exit 1
    fi
}

# Docker Registry 인증 설정
setup_docker_registry() {
    print_step "Docker Registry 인증 설정 중..."
    
    # 로컬 Docker 인증 정보 확인
    if [ -f ~/.docker/config.json ]; then
        # Docker 설정 파일 복사
        ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p ~/.docker"
        scp ~/.docker/config.json "$REMOTE_USER@$REMOTE_HOST:~/.docker/config.json"
        print_success "Docker Registry 인증 설정 완료"
    else
        print_warning "로컬에 Docker 인증 정보가 없습니다. 원격 서버에서 수동 로그인이 필요합니다."
        echo "원격 서버에서 다음 명령어를 실행하세요:"
        echo "ssh $REMOTE_USER@$REMOTE_HOST"
        echo "docker login registry.jclee.me"
    fi
}

# 프로젝트 파일 동기화
sync_project_files() {
    print_step "프로젝트 파일 동기화 중..."
    
    # 원격 서버에 프로젝트 디렉토리 생성
    ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p ~/app"
    
    # rsync로 프로젝트 파일 동기화 (제외 파일 포함)
    rsync -avz --exclude='.git' \
               --exclude='__pycache__' \
               --exclude='*.pyc' \
               --exclude='instance/' \
               --exclude='venv/' \
               --exclude='.env' \
               ./ "$REMOTE_USER@$REMOTE_HOST:~/app/blacklist/"
    
    print_success "프로젝트 파일 동기화 완료"
}

# 검증
verify_setup() {
    print_step "설정 검증 중..."
    
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
echo "=== 설치된 도구 버전 확인 ==="
echo "Docker: $(docker --version 2>/dev/null || echo 'Not installed')"
echo "kubectl: $(kubectl version --client --short 2>/dev/null || echo 'Not installed')"
echo "ArgoCD CLI: $(argocd version --client --short 2>/dev/null || echo 'Not installed')"
echo "Git: $(git --version 2>/dev/null || echo 'Not installed')"
echo ""

echo "=== Kubernetes 연결 확인 ==="
if kubectl cluster-info &> /dev/null; then
    echo "✅ Kubernetes 클러스터 연결 성공"
else
    echo "❌ Kubernetes 클러스터 연결 실패"
fi
echo ""

echo "=== 프로젝트 파일 확인 ==="
if [ -d ~/app/blacklist ]; then
    echo "✅ 프로젝트 파일 동기화 완료"
    echo "파일 수: $(find ~/app/blacklist -type f | wc -l)"
else
    echo "❌ 프로젝트 파일 없음"
fi
EOF
    
    print_success "설정 검증 완료"
}

# 사용법 안내
show_usage() {
    echo ""
    echo "🎯 원격 서버 설정 완료!"
    echo "======================"
    echo ""
    echo "📝 다음 단계:"
    echo "1. 멀티 서버 배포 스크립트 실행:"
    echo "   ./scripts/multi-deploy.sh"
    echo ""
    echo "2. 또는 원격 서버에서 직접 배포:"
    echo "   ssh $REMOTE_USER@$REMOTE_HOST"
    echo "   cd ~/app/blacklist"
    echo "   ./scripts/initial-deploy.sh"
    echo ""
    echo "3. 원격 서버 상태 확인:"
    echo "   ./scripts/check-remote-status.sh"
}

# 메인 실행
main() {
    echo "원격 서버 ($REMOTE_HOST) 설정을 시작합니다."
    echo ""
    read -p "계속하시겠습니까? (y/N): " confirm
    
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "설정을 취소했습니다."
        exit 0
    fi
    
    setup_ssh_keys
    install_remote_tools
    copy_k8s_config
    setup_docker_registry
    sync_project_files
    verify_setup
    show_usage
}

main "$@"