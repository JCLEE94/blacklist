#!/bin/bash

echo "🚀 모든 Kubernetes 클러스터 동시 배포 스크립트"
echo "==========================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 배포 설정
NAMESPACE="blacklist"
REGISTRY_SERVER="registry.jclee.me"
REGISTRY_USER="qws9411"
REGISTRY_PASS="bingogo1"

# 클러스터 설정 파일
CLUSTERS_CONFIG="${HOME}/.kube/clusters.yaml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

print_cluster() {
    local cluster_name=$1
    echo -e "${CYAN}[$cluster_name]${NC} $2"
}

# 클러스터 설정 파일 확인
check_clusters_config() {
    if [ ! -f "$CLUSTERS_CONFIG" ]; then
        print_error "클러스터 설정 파일이 없습니다: $CLUSTERS_CONFIG"
        print_warning "먼저 'kubectl-register-cluster.sh' 스크립트를 실행하여 클러스터를 등록하세요."
        exit 1
    fi
}

# kubectl contexts 목록 가져오기
get_kubectl_contexts() {
    kubectl config get-contexts -o name 2>/dev/null
}

# 활성 클러스터 목록 가져오기 (kubectl contexts 기반)
get_active_clusters() {
    local contexts=$(get_kubectl_contexts)
    if [ -z "$contexts" ]; then
        print_error "등록된 kubectl context가 없습니다."
        exit 1
    fi
    echo "$contexts"
}

# 클러스터에 배포
deploy_to_cluster() {
    local context=$1
    local cluster_name=$2
    local log_file="/tmp/deploy_${cluster_name//[^a-zA-Z0-9]/_}.log"
    
    print_cluster "$cluster_name" "배포 시작..."
    
    (
        echo "=== $cluster_name 배포 시작 $(date) ===" 
        
        # Context 전환
        kubectl config use-context "$context" 2>&1
        
        # 현재 클러스터 정보 확인
        echo "현재 클러스터: $(kubectl config current-context)"
        echo "클러스터 정보: $(kubectl cluster-info | head -n 1)"
        
        # 네임스페이스 생성
        kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f - 2>&1
        
        # 시크릿이 없으면 생성
        if ! kubectl get secret blacklist-secret -n $NAMESPACE &> /dev/null; then
            echo "애플리케이션 시크릿 생성..."
            kubectl create secret generic blacklist-secret \
                --from-literal=REGTECH_USERNAME="nextrade" \
                --from-literal=REGTECH_PASSWORD="Sprtmxm1@3" \
                --from-literal=SECUDIUM_USERNAME="nextrade" \
                --from-literal=SECUDIUM_PASSWORD="Sprtmxm1@3" \
                --from-literal=SECRET_KEY="cluster-${cluster_name}-$(date +%s)" \
                -n $NAMESPACE 2>&1
        fi
        
        if ! kubectl get secret regcred -n $NAMESPACE &> /dev/null; then
            echo "Docker Registry 시크릿 생성..."
            kubectl create secret docker-registry regcred \
                --docker-server=$REGISTRY_SERVER \
                --docker-username="$REGISTRY_USER" \
                --docker-password="$REGISTRY_PASS" \
                -n $NAMESPACE 2>&1
        fi
        
        # Kubernetes 매니페스트 적용
        cd "$PROJECT_ROOT"
        kubectl apply -k k8s/ 2>&1
        
        # ArgoCD가 설치되어 있는 경우에만 ArgoCD 애플리케이션 적용
        if kubectl get namespace argocd &> /dev/null; then
            echo "ArgoCD가 감지됨. ArgoCD 애플리케이션 설정 중..."
            kubectl apply -f k8s/argocd-app-clean.yaml 2>&1
            
            # ArgoCD CLI가 있고 연결 가능한 경우 동기화
            if command -v argocd &> /dev/null; then
                if argocd app list --grpc-web &> /dev/null; then
                    argocd app sync blacklist --grpc-web --timeout 300 2>&1
                else
                    echo "ArgoCD CLI 연결 실패. 수동 동기화 필요."
                fi
            fi
        else
            echo "ArgoCD가 설치되지 않음. 표준 배포만 진행."
        fi
        
        # 배포 상태 확인
        kubectl rollout status deployment/blacklist -n $NAMESPACE --timeout=300s 2>&1
        
        echo "=== $cluster_name 배포 완료 $(date) ==="
    ) > "$log_file" 2>&1 &
    
    local pid=$!
    echo "$pid:$cluster_name:$log_file"
}

# 모든 클러스터에 동시 배포
deploy_to_all_clusters() {
    print_step "등록된 모든 클러스터에 배포 시작..."
    
    local contexts=$(get_active_clusters)
    local deploy_pids=()
    
    # 각 context에 대해 배포 시작
    while IFS= read -r context; do
        # Context 이름을 클러스터 이름으로 사용
        local cluster_name="${context##*/}"  # 마지막 / 이후 부분 추출
        local pid_info=$(deploy_to_cluster "$context" "$cluster_name")
        deploy_pids+=("$pid_info")
    done <<< "$contexts"
    
    # 배포 모니터링
    monitor_all_deployments "${deploy_pids[@]}"
}

# 모든 배포 모니터링
monitor_all_deployments() {
    local pids=("$@")
    local total=${#pids[@]}
    
    print_step "총 $total개 클러스터 배포 진행 중..."
    
    local completed=0
    local start_time=$(date +%s)
    
    # 각 PID 상태 추적
    declare -A status_map
    for pid_info in "${pids[@]}"; do
        IFS=':' read -r pid cluster log <<< "$pid_info"
        status_map[$pid]="진행중:$cluster:$log"
    done
    
    while [ $completed -lt $total ]; do
        local current_completed=0
        
        for pid_info in "${pids[@]}"; do
            IFS=':' read -r pid cluster log <<< "$pid_info"
            
            if ! kill -0 $pid 2>/dev/null; then
                # 프로세스가 종료됨
                if [[ "${status_map[$pid]}" == "진행중:"* ]]; then
                    wait $pid
                    local exit_code=$?
                    if [ $exit_code -eq 0 ]; then
                        status_map[$pid]="완료:$cluster:$log"
                        print_cluster "$cluster" "배포 완료!"
                    else
                        status_map[$pid]="실패:$cluster:$log"
                        print_cluster "$cluster" "배포 실패! (exit code: $exit_code)"
                    fi
                fi
            fi
            
            # 완료된 작업 카운트
            if [[ "${status_map[$pid]}" != "진행중:"* ]]; then
                ((current_completed++))
            fi
        done
        
        completed=$current_completed
        
        # 진행 상황 표시
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        printf "\r경과 시간: ${elapsed}초 | 완료: $completed/$total"
        
        sleep 2
    done
    
    echo "" # 새 줄
}

# 배포 결과 확인
verify_all_deployments() {
    print_step "모든 클러스터 배포 결과 확인..."
    echo ""
    
    local contexts=$(get_active_clusters)
    local success_count=0
    local total_count=0
    
    while IFS= read -r context; do
        ((total_count++))
        local cluster_name="${context##*/}"
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        print_cluster "$cluster_name" "상태 확인"
        
        # Context 전환
        kubectl config use-context "$context" &> /dev/null
        
        # Pod 상태 확인
        if kubectl get pods -n $NAMESPACE 2>/dev/null | grep -q "blacklist"; then
            kubectl get pods -n $NAMESPACE 2>/dev/null
            ((success_count++))
            
            # ArgoCD 상태 확인 (있는 경우)
            if kubectl get namespace argocd &> /dev/null && command -v argocd &> /dev/null; then
                if argocd app get blacklist --grpc-web &> /dev/null; then
                    echo "ArgoCD 상태: $(argocd app get blacklist --grpc-web | grep -E 'Health Status|Sync Status')"
                fi
            fi
        else
            echo "❌ 배포 실패 또는 Pod를 찾을 수 없음"
        fi
    done <<< "$contexts"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    print_step "배포 요약"
    echo "총 클러스터: $total_count"
    echo "성공: $success_count"
    echo "실패: $((total_count - success_count))"
}

# 로그 출력
show_deployment_logs() {
    print_step "배포 로그 확인 (실패한 클러스터만):"
    echo ""
    
    for log_file in /tmp/deploy_*.log; do
        if [ -f "$log_file" ]; then
            # 로그 파일에서 실패 여부 확인
            if grep -q "error\|Error\|ERROR\|failed\|Failed" "$log_file"; then
                local cluster_name=$(basename "$log_file" | sed 's/deploy_//;s/.log$//')
                echo "=== $cluster_name 로그 (마지막 30줄) ==="
                tail -n 30 "$log_file"
                echo ""
            fi
        fi
    done
}

# 접속 정보 표시
show_access_info() {
    echo ""
    echo "🎉 모든 클러스터 배포 작업 완료!"
    echo "================================"
    echo ""
    echo "📊 클러스터별 접속 방법:"
    echo "========================"
    
    local contexts=$(get_active_clusters)
    while IFS= read -r context; do
        local cluster_name="${context##*/}"
        echo ""
        echo "🌐 $cluster_name:"
        echo "- Context 전환: kubectl config use-context $context"
        echo "- Pod 확인: kubectl get pods -n $NAMESPACE"
        echo "- 로그 확인: kubectl logs -f deployment/blacklist -n $NAMESPACE"
        echo "- NodePort 확인: kubectl get svc blacklist -n $NAMESPACE"
    done <<< "$contexts"
}

# 클러스터 선택 메뉴
select_clusters_menu() {
    print_step "배포할 클러스터를 선택하세요:"
    echo ""
    echo "1) 모든 클러스터에 배포"
    echo "2) 특정 클러스터 선택"
    echo "3) 취소"
    echo ""
    read -p "선택 (1-3): " choice
    
    case $choice in
        1)
            return 0  # 모든 클러스터
            ;;
        2)
            # 특정 클러스터 선택 로직
            select_specific_clusters
            ;;
        3)
            echo "배포를 취소했습니다."
            exit 0
            ;;
        *)
            print_error "잘못된 선택입니다."
            exit 1
            ;;
    esac
}

# 메인 실행
main() {
    cd "$PROJECT_ROOT"
    
    # 사전 검사
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl이 설치되지 않았습니다."
        exit 1
    fi
    
    print_step "현재 등록된 Kubernetes contexts:"
    kubectl config get-contexts
    echo ""
    
    # 클러스터 선택
    select_clusters_menu
    
    # 배포 실행
    deploy_to_all_clusters
    
    # 결과 확인
    verify_all_deployments
    show_deployment_logs
    show_access_info
    
    # 원래 context로 복원
    print_step "원래 context로 복원 중..."
    kubectl config use-context $(kubectl config current-context) &> /dev/null
}

# 스크립트 실행
main "$@"