#!/bin/bash

echo "🔧 Kubernetes 클러스터 등록 가이드"
echo "=================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

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

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# 현재 등록된 contexts 표시
show_current_contexts() {
    print_step "현재 등록된 Kubernetes contexts:"
    echo ""
    kubectl config get-contexts
    echo ""
}

# 새 클러스터 추가 메뉴
add_cluster_menu() {
    echo "새 클러스터를 추가하는 방법을 선택하세요:"
    echo ""
    echo "1) kubeconfig 파일로 추가"
    echo "2) 수동으로 클러스터 정보 입력"
    echo "3) 원격 서버에서 kubeconfig 복사"
    echo "4) 취소"
    echo ""
    read -p "선택 (1-4): " choice
    
    case $choice in
        1)
            add_cluster_from_kubeconfig
            ;;
        2)
            add_cluster_manually
            ;;
        3)
            add_cluster_from_remote
            ;;
        4)
            echo "취소되었습니다."
            exit 0
            ;;
        *)
            print_error "잘못된 선택입니다."
            exit 1
            ;;
    esac
}

# kubeconfig 파일로 클러스터 추가
add_cluster_from_kubeconfig() {
    print_step "kubeconfig 파일로 클러스터 추가"
    echo ""
    
    read -p "kubeconfig 파일 경로를 입력하세요: " kubeconfig_path
    
    if [ ! -f "$kubeconfig_path" ]; then
        print_error "파일을 찾을 수 없습니다: $kubeconfig_path"
        exit 1
    fi
    
    # kubeconfig 백업
    print_step "기존 kubeconfig 백업 중..."
    cp ~/.kube/config ~/.kube/config.backup.$(date +%Y%m%d_%H%M%S)
    
    # kubeconfig 병합
    print_step "kubeconfig 병합 중..."
    KUBECONFIG=~/.kube/config:$kubeconfig_path kubectl config view --flatten > ~/.kube/config.new
    mv ~/.kube/config.new ~/.kube/config
    
    print_success "클러스터가 성공적으로 추가되었습니다!"
    show_current_contexts
}

# 수동으로 클러스터 추가
add_cluster_manually() {
    print_step "수동으로 클러스터 정보 입력"
    echo ""
    
    read -p "클러스터 이름: " cluster_name
    read -p "클러스터 API 서버 URL (예: https://192.168.1.100:6443): " api_server
    read -p "인증서 기반 인증을 사용하시겠습니까? (y/n): " use_cert
    
    # 클러스터 추가
    if [[ "$use_cert" =~ ^[Yy]$ ]]; then
        read -p "CA 인증서 파일 경로: " ca_cert_path
        if [ ! -f "$ca_cert_path" ]; then
            print_error "CA 인증서 파일을 찾을 수 없습니다: $ca_cert_path"
            exit 1
        fi
        kubectl config set-cluster "$cluster_name" \
            --server="$api_server" \
            --certificate-authority="$ca_cert_path"
    else
        print_warning "인증서 검증을 건너뜁니다. (보안 위험)"
        kubectl config set-cluster "$cluster_name" \
            --server="$api_server" \
            --insecure-skip-tls-verify=true
    fi
    
    # 사용자 자격 증명 설정
    echo ""
    echo "사용자 인증 방법을 선택하세요:"
    echo "1) 클라이언트 인증서"
    echo "2) Bearer Token"
    echo "3) 사용자명/비밀번호"
    read -p "선택 (1-3): " auth_choice
    
    local user_name="${cluster_name}-user"
    
    case $auth_choice in
        1)
            read -p "클라이언트 인증서 파일 경로: " client_cert
            read -p "클라이언트 키 파일 경로: " client_key
            kubectl config set-credentials "$user_name" \
                --client-certificate="$client_cert" \
                --client-key="$client_key"
            ;;
        2)
            read -p "Bearer Token: " token
            kubectl config set-credentials "$user_name" \
                --token="$token"
            ;;
        3)
            read -p "사용자명: " username
            read -s -p "비밀번호: " password
            echo ""
            kubectl config set-credentials "$user_name" \
                --username="$username" \
                --password="$password"
            ;;
    esac
    
    # Context 생성
    local context_name="${cluster_name}-context"
    kubectl config set-context "$context_name" \
        --cluster="$cluster_name" \
        --user="$user_name" \
        --namespace="default"
    
    print_success "클러스터가 성공적으로 추가되었습니다!"
    
    # 연결 테스트
    print_step "클러스터 연결 테스트 중..."
    kubectl config use-context "$context_name"
    if kubectl cluster-info &> /dev/null; then
        print_success "클러스터 연결 성공!"
        kubectl cluster-info
    else
        print_error "클러스터 연결 실패. 설정을 확인하세요."
    fi
}

# 원격 서버에서 kubeconfig 복사
add_cluster_from_remote() {
    print_step "원격 서버에서 kubeconfig 복사"
    echo ""
    
    read -p "원격 서버 주소 (예: user@192.168.1.100): " remote_server
    read -p "원격 kubeconfig 경로 (기본값: ~/.kube/config): " remote_path
    
    # 기본값 설정
    remote_path=${remote_path:-"~/.kube/config"}
    
    # 임시 파일로 복사
    local temp_config="/tmp/kubeconfig_$(date +%s)"
    
    print_step "원격 서버에서 kubeconfig 복사 중..."
    if scp "$remote_server:$remote_path" "$temp_config"; then
        # 복사된 파일로 클러스터 추가
        add_cluster_from_kubeconfig_file "$temp_config"
        rm -f "$temp_config"
    else
        print_error "원격 서버에서 kubeconfig를 복사할 수 없습니다."
        exit 1
    fi
}

# kubeconfig 파일 처리 (내부 함수)
add_cluster_from_kubeconfig_file() {
    local kubeconfig_path=$1
    
    # kubeconfig 백업
    print_step "기존 kubeconfig 백업 중..."
    cp ~/.kube/config ~/.kube/config.backup.$(date +%Y%m%d_%H%M%S)
    
    # kubeconfig 병합
    print_step "kubeconfig 병합 중..."
    KUBECONFIG=~/.kube/config:$kubeconfig_path kubectl config view --flatten > ~/.kube/config.new
    mv ~/.kube/config.new ~/.kube/config
    
    print_success "클러스터가 성공적으로 추가되었습니다!"
}

# 클러스터 제거
remove_cluster() {
    print_step "클러스터 제거"
    echo ""
    
    # Context 목록 표시
    local contexts=$(kubectl config get-contexts -o name)
    if [ -z "$contexts" ]; then
        print_warning "제거할 context가 없습니다."
        return
    fi
    
    echo "제거할 context를 선택하세요:"
    select context in $contexts "취소"; do
        if [ "$context" = "취소" ]; then
            return
        elif [ -n "$context" ]; then
            # Context에서 클러스터와 사용자 정보 추출
            local cluster=$(kubectl config view -o jsonpath="{.contexts[?(@.name==\"$context\")].context.cluster}")
            local user=$(kubectl config view -o jsonpath="{.contexts[?(@.name==\"$context\")].context.user}")
            
            # 삭제 확인
            echo ""
            print_warning "다음 항목이 삭제됩니다:"
            echo "- Context: $context"
            echo "- Cluster: $cluster"
            echo "- User: $user"
            echo ""
            read -p "정말 삭제하시겠습니까? (y/N): " confirm
            
            if [[ "$confirm" =~ ^[Yy]$ ]]; then
                kubectl config delete-context "$context"
                kubectl config delete-cluster "$cluster"
                kubectl config delete-user "$user"
                print_success "클러스터가 제거되었습니다."
            else
                echo "취소되었습니다."
            fi
            break
        fi
    done
}

# 클러스터 연결 테스트
test_all_clusters() {
    print_step "모든 클러스터 연결 테스트"
    echo ""
    
    local contexts=$(kubectl config get-contexts -o name)
    local current_context=$(kubectl config current-context)
    
    for context in $contexts; do
        echo -e "${CYAN}Testing $context...${NC}"
        kubectl config use-context "$context" &> /dev/null
        
        if kubectl cluster-info &> /dev/null; then
            local server=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
            print_success "$context: 연결 성공 ($server)"
        else
            print_error "$context: 연결 실패"
        fi
        echo ""
    done
    
    # 원래 context로 복원
    kubectl config use-context "$current_context" &> /dev/null
}

# ArgoCD 설정 가이드
show_argocd_setup() {
    print_step "ArgoCD 멀티 클러스터 설정 가이드"
    echo ""
    echo "ArgoCD에서 멀티 클러스터를 관리하려면:"
    echo ""
    echo "1. ArgoCD가 설치된 메인 클러스터에서 실행:"
    echo "   ${CYAN}argocd cluster add <context-name>${NC}"
    echo ""
    echo "2. 또는 수동으로 클러스터 추가:"
    echo "   ${CYAN}kubectl create secret generic cluster-<name> \\
      --from-literal=name=<cluster-name> \\
      --from-literal=server=<api-server-url> \\
      --from-literal=config=<kubeconfig-content> \\
      -n argocd${NC}"
    echo ""
    echo "3. 클러스터 목록 확인:"
    echo "   ${CYAN}argocd cluster list${NC}"
    echo ""
}

# 메인 메뉴
main_menu() {
    while true; do
        echo ""
        echo "🔧 Kubernetes 클러스터 관리"
        echo "==========================="
        echo ""
        echo "1) 현재 클러스터 목록 보기"
        echo "2) 새 클러스터 추가"
        echo "3) 클러스터 제거"
        echo "4) 모든 클러스터 연결 테스트"
        echo "5) ArgoCD 멀티 클러스터 설정 가이드"
        echo "6) 종료"
        echo ""
        read -p "선택 (1-6): " choice
        
        case $choice in
            1)
                show_current_contexts
                ;;
            2)
                add_cluster_menu
                ;;
            3)
                remove_cluster
                ;;
            4)
                test_all_clusters
                ;;
            5)
                show_argocd_setup
                ;;
            6)
                echo "종료합니다."
                exit 0
                ;;
            *)
                print_error "잘못된 선택입니다."
                ;;
        esac
    done
}

# 사전 검사
check_prerequisites() {
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl이 설치되지 않았습니다."
        echo "설치 방법: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    
    if [ ! -d ~/.kube ]; then
        mkdir -p ~/.kube
    fi
    
    if [ ! -f ~/.kube/config ]; then
        touch ~/.kube/config
    fi
}

# 메인 실행
main() {
    check_prerequisites
    
    # 인자가 있으면 직접 실행
    case "${1:-}" in
        add)
            add_cluster_menu
            ;;
        remove)
            remove_cluster
            ;;
        list)
            show_current_contexts
            ;;
        test)
            test_all_clusters
            ;;
        *)
            main_menu
            ;;
    esac
}

# 스크립트 실행
main "$@"