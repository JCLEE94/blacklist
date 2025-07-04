#!/bin/bash

echo "🚀 멀티 서버 동시 배포 스크립트"
echo "=============================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 서버 정보
LOCAL_NAME="로컬 서버"
REMOTE_HOST="192.168.50.110"
REMOTE_USER="jclee"
REMOTE_NAME="원격 서버 ($REMOTE_HOST)"

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

print_local() {
    echo -e "${PURPLE}[LOCAL]${NC} $1"
}

print_remote() {
    echo -e "${BLUE}[REMOTE]${NC} $1"
}

# 사전 검사
check_prerequisites() {
    print_step "사전 요구사항 확인 중..."
    
    # SSH 연결 확인
    if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "echo 'test'" &> /dev/null; then
        print_error "원격 서버 SSH 연결 실패. 먼저 ./scripts/setup/remote-server-setup.sh를 실행하세요."
        exit 1
    fi
    
    # 로컬 도구 확인
    for tool in kubectl argocd docker; do
        if ! command -v $tool &> /dev/null; then
            print_error "로컬에 $tool이 설치되지 않았습니다."
            exit 1
        fi
    done
    
    # 원격 도구 확인
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
for tool in kubectl argocd docker; do
    if ! command -v $tool &> /dev/null; then
        echo "ERROR: 원격 서버에 $tool이 설치되지 않았습니다."
        exit 1
    fi
done
EOF
    
    print_success "사전 요구사항 확인 완료"
}

# 프로젝트 파일 동기화
sync_project() {
    print_step "프로젝트 파일 동기화 중..."
    
    # 원격 서버로 최신 파일 동기화
    rsync -avz --delete \
               --exclude='.git' \
               --exclude='__pycache__' \
               --exclude='*.pyc' \
               --exclude='instance/' \
               --exclude='venv/' \
               --exclude='.env' \
               ./ "$REMOTE_USER@$REMOTE_HOST:~/app/blacklist/"
    
    print_success "프로젝트 파일 동기화 완료"
}

# 로컬 배포 함수
deploy_local() {
    print_local "로컬 서버 배포 시작..."
    
    # 로그 파일 설정
    local log_file="/tmp/local_deploy.log"
    
    (
        echo "=== 로컬 배포 시작 $(date) ===" 
        
        # 네임스페이스 생성
        kubectl create namespace blacklist --dry-run=client -o yaml | kubectl apply -f - 2>&1
        
        # 시크릿이 없으면 생성 (이미 있으면 스킵)
        if ! kubectl get secret blacklist-secret -n blacklist &> /dev/null; then
            echo "시크릿이 없어 기본값으로 생성합니다..."
            kubectl create secret generic blacklist-secret \
                --from-literal=REGTECH_USERNAME="nextrade" \
                --from-literal=REGTECH_PASSWORD="Sprtmxm1@3" \
                --from-literal=SECUDIUM_USERNAME="nextrade" \
                --from-literal=SECUDIUM_PASSWORD="Sprtmxm1@3" \
                --from-literal=SECRET_KEY="local-secret-key-$(date +%s)" \
                -n blacklist 2>&1
        fi
        
        if ! kubectl get secret regcred -n blacklist &> /dev/null; then
            echo "Docker Registry 시크릿이 없어 기본값으로 생성합니다..."
            kubectl create secret docker-registry regcred \
                --docker-server=registry.jclee.me \
                --docker-username="qws9411" \
                --docker-password="bingogo1" \
                -n blacklist 2>&1
        fi
        
        # Kubernetes 매니페스트 적용
        kubectl apply -k k8s/ 2>&1
        
        # ArgoCD 애플리케이션 적용
        kubectl apply -f k8s/argocd-app-clean.yaml 2>&1
        
        # ArgoCD 동기화
        if command -v argocd &> /dev/null; then
            argocd app sync blacklist --grpc-web --timeout 300 2>&1
        fi
        
        # 배포 대기
        kubectl rollout status deployment/blacklist -n blacklist --timeout=300s 2>&1
        
        echo "=== 로컬 배포 완료 $(date) ==="
    ) > "$log_file" 2>&1 &
    
    local local_pid=$!
    echo "로컬 배포 PID: $local_pid (로그: $log_file)"
    
    return $local_pid
}

# 원격 배포 함수
deploy_remote() {
    print_remote "원격 서버 배포 시작..."
    
    # 로그 파일 설정
    local log_file="/tmp/remote_deploy.log"
    
    (
        ssh "$REMOTE_USER@$REMOTE_HOST" << 'REMOTE_EOF'
echo "=== 원격 배포 시작 $(date) ==="

cd ~/app/blacklist

# 네임스페이스 생성
kubectl create namespace blacklist --dry-run=client -o yaml | kubectl apply -f -

# 시크릿이 없으면 생성
if ! kubectl get secret blacklist-secret -n blacklist &> /dev/null; then
    echo "시크릿이 없어 기본값으로 생성합니다..."
    kubectl create secret generic blacklist-secret \
        --from-literal=REGTECH_USERNAME="nextrade" \
        --from-literal=REGTECH_PASSWORD="Sprtmxm1@3" \
        --from-literal=SECUDIUM_USERNAME="nextrade" \
        --from-literal=SECUDIUM_PASSWORD="Sprtmxm1@3" \
        --from-literal=SECRET_KEY="remote-secret-key-$(date +%s)" \
        -n blacklist
fi

if ! kubectl get secret regcred -n blacklist &> /dev/null; then
    echo "Docker Registry 시크릿이 없어 기본값으로 생성합니다..."
    kubectl create secret docker-registry regcred \
        --docker-server=registry.jclee.me \
        --docker-username="qws9411" \
        --docker-password="bingogo1" \
        -n blacklist
fi

# Kubernetes 매니페스트 적용
kubectl apply -k k8s/

# ArgoCD 애플리케이션 적용
kubectl apply -f k8s/argocd-app-clean.yaml

# ArgoCD 동기화
if command -v argocd &> /dev/null; then
    argocd app sync blacklist --grpc-web --timeout 300
fi

# 배포 대기
kubectl rollout status deployment/blacklist -n blacklist --timeout=300s

echo "=== 원격 배포 완료 $(date) ==="
REMOTE_EOF
    ) > "$log_file" 2>&1 &
    
    local remote_pid=$!
    echo "원격 배포 PID: $remote_pid (로그: $log_file)"
    
    return $remote_pid
}

# 배포 상태 모니터링
monitor_deployments() {
    local local_pid=$1
    local remote_pid=$2
    
    print_step "배포 진행 상황 모니터링 중..."
    
    local local_done=false
    local remote_done=false
    local start_time=$(date +%s)
    
    while [[ "$local_done" = false || "$remote_done" = false ]]; do
        # 로컬 배포 상태 확인
        if [[ "$local_done" = false ]]; then
            if ! kill -0 $local_pid 2>/dev/null; then
                wait $local_pid
                local local_exit_code=$?
                if [ $local_exit_code -eq 0 ]; then
                    print_local "배포 완료!"
                else
                    print_local "배포 실패 (exit code: $local_exit_code)"
                fi
                local_done=true
            fi
        fi
        
        # 원격 배포 상태 확인
        if [[ "$remote_done" = false ]]; then
            if ! kill -0 $remote_pid 2>/dev/null; then
                wait $remote_pid
                local remote_exit_code=$?
                if [ $remote_exit_code -eq 0 ]; then
                    print_remote "배포 완료!"
                else
                    print_remote "배포 실패 (exit code: $remote_exit_code)"
                fi
                remote_done=true
            fi
        fi
        
        # 진행 상황 표시
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        printf "\r경과 시간: ${elapsed}초 | 로컬: %s | 원격: %s" \
               "$([ "$local_done" = true ] && echo "완료" || echo "진행중")" \
               "$([ "$remote_done" = true ] && echo "완료" || echo "진행중")"
        
        sleep 2
    done
    
    echo "" # 새 줄
}

# 배포 결과 확인
verify_deployments() {
    print_step "배포 결과 확인 중..."
    
    echo ""
    print_local "로컬 서버 상태:"
    echo "=================="
    kubectl get pods -n blacklist 2>/dev/null || echo "❌ 로컬 배포 실패"
    
    echo ""
    print_remote "원격 서버 상태:"
    echo "=================="
    ssh "$REMOTE_USER@$REMOTE_HOST" "kubectl get pods -n blacklist" 2>/dev/null || echo "❌ 원격 배포 실패"
    
    echo ""
    print_step "ArgoCD 애플리케이션 상태:"
    echo "=========================="
    
    # 로컬 ArgoCD 상태
    if argocd app get blacklist --grpc-web &> /dev/null; then
        echo "로컬 ArgoCD: $(argocd app get blacklist --grpc-web | grep -E 'Health Status|Sync Status')"
    else
        echo "로컬 ArgoCD: 연결 불가"
    fi
    
    # 원격 ArgoCD 상태
    remote_argocd_status=$(ssh "$REMOTE_USER@$REMOTE_HOST" "argocd app get blacklist --grpc-web 2>/dev/null | grep -E 'Health Status|Sync Status'" 2>/dev/null || echo "연결 불가")
    echo "원격 ArgoCD: $remote_argocd_status"
}

# 로그 출력
show_logs() {
    print_step "배포 로그 확인:"
    
    echo ""
    echo "=== 로컬 배포 로그 ==="
    if [ -f /tmp/local_deploy.log ]; then
        tail -n 20 /tmp/local_deploy.log
    else
        echo "로그 파일 없음"
    fi
    
    echo ""
    echo "=== 원격 배포 로그 ==="
    if [ -f /tmp/remote_deploy.log ]; then
        tail -n 20 /tmp/remote_deploy.log
    else
        echo "로그 파일 없음"
    fi
}

# 접속 정보 안내
show_access_info() {
    echo ""
    echo "🎉 멀티 서버 배포 완료!"
    echo "======================"
    echo ""
    echo "📊 접속 정보:"
    echo "============"
    echo ""
    echo "🏠 로컬 서버:"
    echo "- 프로덕션: https://blacklist.jclee.me"
    echo "- NodePort: http://localhost:32542"
    echo "- ArgoCD: https://argo.jclee.me/applications/blacklist"
    echo ""
    echo "🌐 원격 서버 ($REMOTE_HOST):"
    echo "- NodePort: http://$REMOTE_HOST:32542"
    echo "- 직접 접속: ssh $REMOTE_USER@$REMOTE_HOST"
    echo ""
    echo "🔍 상태 확인 명령어:"
    echo "kubectl get pods -n blacklist                    # 로컬"
    echo "ssh $REMOTE_USER@$REMOTE_HOST 'kubectl get pods -n blacklist'  # 원격"
}

# 메인 실행
main() {
    echo "이 스크립트는 로컬과 원격 서버에 동시 배포를 수행합니다."
    echo ""
    echo "대상 서버:"
    echo "- 로컬: $(hostname)"
    echo "- 원격: $REMOTE_HOST"
    echo ""
    read -p "계속하시겠습니까? (y/N): " confirm
    
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "배포를 취소했습니다."
        exit 0
    fi
    
    check_prerequisites
    sync_project
    
    # 동시 배포 시작
    print_step "동시 배포 시작..."
    deploy_local
    local_pid=$?
    
    deploy_remote  
    remote_pid=$?
    
    # 배포 모니터링
    monitor_deployments $local_pid $remote_pid
    
    # 결과 확인
    verify_deployments
    show_logs
    show_access_info
}

main "$@"