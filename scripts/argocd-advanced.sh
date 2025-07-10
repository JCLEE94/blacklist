#!/bin/bash

# ArgoCD 고급 관리 스크립트
# ArgoCD CLI를 사용한 고급 기능 제공

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 설정
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"
APP_NAME="blacklist"
NAMESPACE="blacklist"

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
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

show_usage() {
    echo "사용법: $0 <command> [options]"
    echo ""
    echo "명령어:"
    echo "  diff              - Git과 실제 배포 상태 차이 확인"
    echo "  manifest          - 렌더링된 매니페스트 확인"
    echo "  refresh           - 리소스 새로고침"
    echo "  resources         - 모든 리소스 상태 확인"
    echo "  set-image <tag>   - 이미지 태그 업데이트"
    echo "  promote <env>     - 환경 간 프로모션"
    echo "  backup            - 애플리케이션 설정 백업"
    echo "  restore <file>    - 애플리케이션 설정 복원"
    echo "  health            - 상세 헬스 체크"
    echo "  events            - 애플리케이션 이벤트"
    echo "  metrics           - 메트릭 및 통계"
    echo ""
    echo "옵션:"
    echo "  --revision <rev>  - 특정 Git revision 사용"
    echo "  --local           - 로컬 매니페스트 사용"
}

# ArgoCD 로그인 확인
check_argocd_login() {
    if ! argocd account whoami --grpc-web &> /dev/null; then
        print_error "ArgoCD에 로그인되지 않았습니다."
        echo "다음 명령으로 로그인하세요:"
        echo "  argocd login $ARGOCD_SERVER --grpc-web"
        exit 1
    fi
}

# Git과 실제 상태 차이 확인
show_diff() {
    print_header "Git vs Live 상태 비교"
    
    argocd app diff $APP_NAME --grpc-web || {
        print_warning "차이가 없거나 앱이 동기화되지 않았습니다."
    }
}

# 렌더링된 매니페스트 확인
show_manifest() {
    print_header "렌더링된 Kubernetes 매니페스트"
    
    local revision="${REVISION:-HEAD}"
    
    echo -e "${YELLOW}Revision: $revision${NC}"
    argocd app manifests $APP_NAME --revision $revision --grpc-web
}

# 리소스 새로고침
refresh_resources() {
    print_header "리소스 새로고침"
    
    argocd app get $APP_NAME --refresh --grpc-web
    print_success "리소스가 새로고침되었습니다."
}

# 모든 리소스 상태 확인
show_resources() {
    print_header "애플리케이션 리소스 상태"
    
    argocd app resources $APP_NAME --grpc-web
    
    echo ""
    echo -e "${YELLOW}Pod 상태:${NC}"
    kubectl get pods -n $NAMESPACE -l app=blacklist
}

# 이미지 태그 업데이트
set_image() {
    local tag="$1"
    
    if [ -z "$tag" ]; then
        print_error "이미지 태그를 지정하세요."
        echo "예: $0 set-image v1.2.3"
        exit 1
    fi
    
    print_header "이미지 태그 업데이트: $tag"
    
    # Kustomize를 사용하여 이미지 업데이트
    cd k8s
    kustomize edit set image ghcr.io/jclee94/blacklist:latest=ghcr.io/jclee94/blacklist:$tag
    
    # Git commit & push
    git add .
    git commit -m "chore: update image to $tag"
    git push origin main
    
    print_success "이미지가 $tag로 업데이트되었습니다."
    echo "ArgoCD가 자동으로 동기화합니다..."
}

# 환경 간 프로모션
promote_environment() {
    local target_env="$1"
    
    if [ -z "$target_env" ]; then
        print_error "대상 환경을 지정하세요."
        echo "예: $0 promote production"
        exit 1
    fi
    
    print_header "환경 프로모션: $target_env"
    
    # 현재 버전 확인
    local current_image=$(argocd app get $APP_NAME -o json --grpc-web | jq -r '.status.summary.images[0]')
    echo -e "${YELLOW}현재 이미지: $current_image${NC}"
    
    # 프로모션 확인
    echo -e "${YELLOW}이 이미지를 $target_env 환경으로 프로모션하시겠습니까? (y/n)${NC}"
    read -r confirm
    
    if [[ "$confirm" == "y" ]]; then
        # 대상 환경의 kustomization 업데이트
        cd k8s/overlays/$target_env 2>/dev/null || {
            print_error "$target_env 환경 디렉토리가 없습니다."
            exit 1
        }
        
        kustomize edit set image blacklist=$current_image
        git add .
        git commit -m "chore: promote $current_image to $target_env"
        git push origin main
        
        print_success "$target_env 환경으로 프로모션 완료"
    else
        print_warning "프로모션이 취소되었습니다."
    fi
}

# 애플리케이션 설정 백업
backup_application() {
    print_header "애플리케이션 설정 백업"
    
    local backup_file="argocd-backup-$(date +%Y%m%d-%H%M%S).yaml"
    
    argocd app get $APP_NAME -o yaml --grpc-web > $backup_file
    
    print_success "백업이 $backup_file에 저장되었습니다."
}

# 애플리케이션 설정 복원
restore_application() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        print_error "백업 파일을 찾을 수 없습니다: $backup_file"
        exit 1
    fi
    
    print_header "애플리케이션 설정 복원"
    
    echo -e "${YELLOW}경고: 현재 설정이 덮어씌워집니다. 계속하시겠습니까? (y/n)${NC}"
    read -r confirm
    
    if [[ "$confirm" == "y" ]]; then
        kubectl apply -f $backup_file
        print_success "애플리케이션이 복원되었습니다."
    else
        print_warning "복원이 취소되었습니다."
    fi
}

# 상세 헬스 체크
show_health() {
    print_header "상세 헬스 체크"
    
    # ArgoCD 헬스 상태
    echo -e "${YELLOW}ArgoCD 헬스 상태:${NC}"
    argocd app get $APP_NAME --grpc-web | grep -E "Health Status:|Sync Status:"
    
    # Pod 헬스 체크
    echo -e "\n${YELLOW}Pod 헬스 체크:${NC}"
    kubectl get pods -n $NAMESPACE -l app=blacklist -o wide
    
    # 엔드포인트 헬스 체크
    echo -e "\n${YELLOW}엔드포인트 헬스 체크:${NC}"
    local pod=$(kubectl get pod -n $NAMESPACE -l app=blacklist -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$pod" ]; then
        kubectl exec -n $NAMESPACE $pod -- curl -s http://localhost:2541/health || echo "헬스 체크 실패"
    fi
}

# 애플리케이션 이벤트
show_events() {
    print_header "애플리케이션 이벤트"
    
    # ArgoCD 이벤트
    echo -e "${YELLOW}ArgoCD 애플리케이션 이벤트:${NC}"
    argocd app events $APP_NAME --grpc-web
    
    # Kubernetes 이벤트
    echo -e "\n${YELLOW}Kubernetes 이벤트 (최근 10개):${NC}"
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10
}

# 메트릭 및 통계
show_metrics() {
    print_header "메트릭 및 통계"
    
    # 리소스 사용량
    echo -e "${YELLOW}리소스 사용량:${NC}"
    kubectl top pods -n $NAMESPACE -l app=blacklist 2>/dev/null || echo "메트릭 서버가 설치되지 않았습니다."
    
    # 배포 통계
    echo -e "\n${YELLOW}배포 통계:${NC}"
    kubectl get deployment blacklist -n $NAMESPACE -o json | jq '{
        replicas: .spec.replicas,
        ready: .status.readyReplicas,
        available: .status.availableReplicas,
        updated: .status.updatedReplicas
    }'
    
    # ArgoCD 동기화 통계
    echo -e "\n${YELLOW}ArgoCD 동기화 정보:${NC}"
    argocd app get $APP_NAME --grpc-web -o json | jq '{
        sync_status: .status.sync.status,
        health_status: .status.health.status,
        last_sync: .status.operationState.finishedAt,
        revision: .status.sync.revision
    }'
}

# 메인 함수
main() {
    local command="$1"
    shift
    
    # 옵션 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            --revision)
                REVISION="$2"
                shift 2
                ;;
            --local)
                LOCAL=true
                shift
                ;;
            *)
                break
                ;;
        esac
    done
    
    # ArgoCD 로그인 확인
    check_argocd_login
    
    # 명령 실행
    case "$command" in
        diff)
            show_diff
            ;;
        manifest)
            show_manifest
            ;;
        refresh)
            refresh_resources
            ;;
        resources)
            show_resources
            ;;
        set-image)
            set_image "$1"
            ;;
        promote)
            promote_environment "$1"
            ;;
        backup)
            backup_application
            ;;
        restore)
            restore_application "$1"
            ;;
        health)
            show_health
            ;;
        events)
            show_events
            ;;
        metrics)
            show_metrics
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"