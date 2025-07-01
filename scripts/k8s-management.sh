#!/bin/bash

# Blacklist Kubernetes 관리 스크립트
# 작성자: Claude
# 설명: Kubernetes 배포 관리를 위한 통합 스크립트

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정
NAMESPACE="blacklist"
APP_NAME="blacklist"
REGISTRY="registry.jclee.me"
IMAGE="${REGISTRY}/${APP_NAME}"
KUSTOMIZE_DIR="./k8s"

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 사용법 출력
usage() {
    echo "사용법: $0 [명령] [옵션]"
    echo ""
    echo "명령:"
    echo "  init          - 초기 배포 (네임스페이스, 시크릿, 볼륨 생성)"
    echo "  deploy        - 애플리케이션 배포/업데이트"
    echo "  restart       - 디플로이먼트 재시작"
    echo "  rollback      - 이전 버전으로 롤백"
    echo "  status        - 배포 상태 확인"
    echo "  logs          - 로그 확인"
    echo "  scale         - 파드 스케일 조정"
    echo "  delete        - 모든 리소스 삭제"
    echo "  port-forward  - 로컬 포트 포워딩"
    echo "  exec          - 파드에 명령 실행"
    echo "  describe      - 리소스 상세 정보"
    echo "  events        - 이벤트 확인"
    echo ""
    echo "옵션:"
    echo "  -t, --tag     - 이미지 태그 (기본값: latest)"
    echo "  -r, --replicas - 레플리카 수 (scale 명령용)"
    echo "  -p, --pod     - 파드 이름 (logs, exec 명령용)"
    echo ""
    echo "예제:"
    echo "  $0 init"
    echo "  $0 deploy --tag v1.2.3"
    echo "  $0 scale --replicas 5"
    echo "  $0 logs --pod blacklist-xyz"
}

# 네임스페이스 확인 및 생성
ensure_namespace() {
    if ! kubectl get namespace $NAMESPACE &>/dev/null; then
        log_info "네임스페이스 '$NAMESPACE' 생성 중..."
        kubectl create namespace $NAMESPACE
        log_success "네임스페이스 생성 완료"
    else
        log_info "네임스페이스 '$NAMESPACE' 이미 존재"
    fi
}

# 초기 배포
init_deployment() {
    log_info "초기 배포 시작..."
    
    # 네임스페이스 생성
    ensure_namespace
    
    # Docker 레지스트리 시크릿 생성
    if ! kubectl get secret regcred -n $NAMESPACE &>/dev/null; then
        log_info "Docker 레지스트리 시크릿 생성 중..."
        read -p "Docker 사용자명: " docker_user
        read -s -p "Docker 비밀번호: " docker_pass
        echo
        
        kubectl create secret docker-registry regcred \
            --docker-server=$REGISTRY \
            --docker-username=$docker_user \
            --docker-password=$docker_pass \
            -n $NAMESPACE
        
        log_success "Docker 레지스트리 시크릿 생성 완료"
    fi
    
    # Kustomize로 배포
    log_info "Kustomize로 리소스 배포 중..."
    kubectl apply -k $KUSTOMIZE_DIR
    
    # 배포 대기
    log_info "배포 완료 대기 중..."
    kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=1200s
    
    log_success "초기 배포 완료!"
}

# 애플리케이션 배포/업데이트
deploy_app() {
    local tag="${TAG:-latest}"
    
    log_info "애플리케이션 배포 시작 (태그: $tag)..."
    
    # 이미지 태그 업데이트
    if command -v kustomize &>/dev/null; then
        cd $KUSTOMIZE_DIR
        kustomize edit set image ${IMAGE}:${tag}
        cd - > /dev/null
    fi
    
    # 배포
    kubectl apply -k $KUSTOMIZE_DIR
    
    # 롤아웃 상태 비동기 확인
    log_info "배포가 시작되었습니다. 진행 상황 확인 중..."
    
    # 즉시 Pod 상태 확인
    kubectl get pods -n $NAMESPACE -l app=$APP_NAME
    
    # 비동기로 상태 확인 (--watch=false로 즉시 반환)
    if kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --watch=false; then
        log_success "배포가 진행 중입니다!"
    else
        log_warning "배포가 아직 진행 중입니다. 수동으로 확인하세요:"
        echo "kubectl rollout status deployment/$APP_NAME -n $NAMESPACE"
    fi
    
    log_info "배포 모니터링: kubectl get pods -n $NAMESPACE -w"
}

# 디플로이먼트 재시작
restart_deployment() {
    log_info "디플로이먼트 재시작 중..."
    kubectl rollout restart deployment/$APP_NAME -n $NAMESPACE
    
    log_info "재시작 완료 대기 중..."
    kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=1200s
    
    log_success "재시작 완료!"
}

# 롤백
rollback_deployment() {
    log_info "이전 버전으로 롤백 중..."
    kubectl rollout undo deployment/$APP_NAME -n $NAMESPACE
    
    log_info "롤백 완료 대기 중..."
    kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=1200s
    
    log_success "롤백 완료!"
}

# 상태 확인
check_status() {
    log_info "배포 상태 확인..."
    echo ""
    
    echo "=== 디플로이먼트 ==="
    kubectl get deployments -n $NAMESPACE
    echo ""
    
    echo "=== 파드 ==="
    kubectl get pods -n $NAMESPACE -o wide
    echo ""
    
    echo "=== 서비스 ==="
    kubectl get services -n $NAMESPACE
    echo ""
    
    echo "=== 인그레스 ==="
    kubectl get ingress -n $NAMESPACE
    echo ""
    
    echo "=== HPA ==="
    kubectl get hpa -n $NAMESPACE
}

# 로그 확인
view_logs() {
    local pod_name="${POD:-}"
    
    if [ -z "$pod_name" ]; then
        # 첫 번째 파드 선택
        pod_name=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME -o jsonpath='{.items[0].metadata.name}')
    fi
    
    if [ -z "$pod_name" ]; then
        log_error "실행 중인 파드를 찾을 수 없습니다"
        exit 1
    fi
    
    log_info "파드 '$pod_name'의 로그 확인..."
    kubectl logs -f $pod_name -n $NAMESPACE
}

# 스케일 조정
scale_deployment() {
    local replicas="${REPLICAS:-3}"
    
    log_info "레플리카 수를 $replicas로 조정 중..."
    kubectl scale deployment/$APP_NAME -n $NAMESPACE --replicas=$replicas
    
    log_info "스케일 조정 완료 대기 중..."
    kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=1200s
    
    log_success "스케일 조정 완료!"
}

# 모든 리소스 삭제
delete_all() {
    log_warning "모든 리소스를 삭제합니다. 계속하시겠습니까? (y/N)"
    read -r confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "삭제 취소됨"
        exit 0
    fi
    
    log_info "모든 리소스 삭제 중..."
    kubectl delete -k $KUSTOMIZE_DIR
    
    log_success "삭제 완료!"
}

# 포트 포워딩
port_forward() {
    local pod_name=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$pod_name" ]; then
        log_error "실행 중인 파드를 찾을 수 없습니다"
        exit 1
    fi
    
    log_info "포트 포워딩 설정 (로컬 8541 -> 파드 2541)..."
    kubectl port-forward $pod_name 8541:2541 -n $NAMESPACE
}

# 파드에 명령 실행
exec_in_pod() {
    local pod_name="${POD:-}"
    
    if [ -z "$pod_name" ]; then
        pod_name=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME -o jsonpath='{.items[0].metadata.name}')
    fi
    
    if [ -z "$pod_name" ]; then
        log_error "실행 중인 파드를 찾을 수 없습니다"
        exit 1
    fi
    
    log_info "파드 '$pod_name'에 접속 중..."
    kubectl exec -it $pod_name -n $NAMESPACE -- /bin/bash
}

# 리소스 상세 정보
describe_resources() {
    log_info "리소스 상세 정보..."
    
    echo "=== 디플로이먼트 ==="
    kubectl describe deployment/$APP_NAME -n $NAMESPACE
    
    echo -e "\n=== 최신 파드 ==="
    local pod_name=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME -o jsonpath='{.items[0].metadata.name}')
    if [ -n "$pod_name" ]; then
        kubectl describe pod/$pod_name -n $NAMESPACE
    fi
}

# 이벤트 확인
view_events() {
    log_info "최근 이벤트 확인..."
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -20
}

# 메인 함수
main() {
    # 옵션 파싱
    TAG=""
    REPLICAS=""
    POD=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tag)
                TAG="$2"
                shift 2
                ;;
            -r|--replicas)
                REPLICAS="$2"
                shift 2
                ;;
            -p|--pod)
                POD="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                break
                ;;
        esac
    done
    
    # 명령 실행
    case "${1:-}" in
        init)
            init_deployment
            ;;
        deploy)
            deploy_app
            ;;
        restart)
            restart_deployment
            ;;
        rollback)
            rollback_deployment
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs
            ;;
        scale)
            scale_deployment
            ;;
        delete)
            delete_all
            ;;
        port-forward)
            port_forward
            ;;
        exec)
            exec_in_pod
            ;;
        describe)
            describe_resources
            ;;
        events)
            view_events
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"