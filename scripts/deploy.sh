#!/bin/bash

#
# Blacklist Management System - 배포 스크립트
# jclee.me 인프라 전용 배포 스크립트
#

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 기본 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NAMESPACE="blacklist"
REGISTRY="registry.jclee.me"
IMAGE_NAME="jclee94/blacklist"
ARGOCD_SERVER="argo.jclee.me"

# 환경 변수 (기본값 설정)
ENVIRONMENT="${ENVIRONMENT:-development}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DRY_RUN="${DRY_RUN:-false}"
FORCE_REBUILD="${FORCE_REBUILD:-false}"
SKIP_TESTS="${SKIP_TESTS:-false}"

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
    echo -e "${PURPLE}[INFO]${NC} $1"
}

show_usage() {
    echo "Blacklist Management System - 배포 스크립트"
    echo ""
    echo "사용법: $0 [OPTIONS] COMMAND"
    echo ""
    echo "COMMANDS:"
    echo "  build         - Docker 이미지 빌드 및 푸시"
    echo "  deploy        - Kubernetes 배포"
    echo "  test          - 테스트 실행"
    echo "  full          - 전체 파이프라인 (빌드 + 테스트 + 배포)"
    echo "  rollback      - 이전 버전으로 롤백"
    echo "  status        - 배포 상태 확인"
    echo "  logs          - 애플리케이션 로그"
    echo "  cleanup       - 리소스 정리"
    echo ""
    echo "OPTIONS:"
    echo "  -e, --env ENV          환경 (development|staging|production) [기본: development]"
    echo "  -t, --tag TAG          이미지 태그 [기본: latest]"
    echo "  -f, --force            강제 빌드/배포"
    echo "  -d, --dry-run          실제 실행 없이 명령어만 출력"
    echo "  -s, --skip-tests       테스트 건너뛰기"
    echo "  -h, --help             도움말"
    echo ""
    echo "예시:"
    echo "  $0 build -t v1.2.3"
    echo "  $0 deploy -e production -t v1.2.3"
    echo "  $0 full -e staging"
    echo "  $0 rollback -e production"
}

check_prerequisites() {
    print_step "사전 요구사항 확인 중..."
    
    # 필수 도구 확인
    local tools=("docker" "kubectl" "git")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            print_error "$tool이 설치되지 않았습니다."
            exit 1
        fi
    done
    
    # Kubernetes 클러스터 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Kubernetes 클러스터에 연결할 수 없습니다."
        exit 1
    fi
    
    # Docker 레지스트리 로그인 확인
    if ! docker info | grep -q "Registry:"; then
        print_warning "Docker 레지스트리 로그인이 필요할 수 있습니다."
    fi
    
    print_success "사전 요구사항 확인 완료"
}

load_environment() {
    print_step "환경 설정 로드 중..."
    
    # .env 파일 로드 (있는 경우)
    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        set -a
        source "${PROJECT_ROOT}/.env"
        set +a
        print_info ".env 파일 로드 완료"
    fi
    
    # 환경별 설정
    case "$ENVIRONMENT" in
        development)
            NAMESPACE="${NAMESPACE}-dev"
            ;;
        staging)
            NAMESPACE="${NAMESPACE}-staging"
            ;;
        production)
            NAMESPACE="$NAMESPACE"
            ;;
        *)
            print_error "지원하지 않는 환경: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    print_info "Environment: $ENVIRONMENT"
    print_info "Namespace: $NAMESPACE"
    print_info "Image Tag: $IMAGE_TAG"
}

run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        print_warning "테스트 건너뛰기"
        return 0
    fi
    
    print_step "테스트 실행 중..."
    
    cd "$PROJECT_ROOT"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "PYTHONPATH=${PROJECT_ROOT} pytest tests/ -v --cov=src"
        return 0
    fi
    
    # 테스트 환경 설정
    export PYTHONPATH="${PROJECT_ROOT}"
    export TEST_MODE="true"
    export FORCE_DISABLE_COLLECTION="true"
    export COLLECTION_ENABLED="false"
    
    # 가상환경 설정 (있는 경우)
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
        print_info "Python 가상환경 활성화"
    fi
    
    # 테스트 실행
    if python -m pytest tests/ -v --cov=src --cov-report=term-missing; then
        print_success "모든 테스트 통과"
    else
        print_error "테스트 실패"
        exit 1
    fi
}

build_image() {
    print_step "Docker 이미지 빌드 중..."
    
    cd "$PROJECT_ROOT"
    
    # 이미지 태그 생성
    local full_tag="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    local latest_tag="${REGISTRY}/${IMAGE_NAME}:latest"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "docker build -t $full_tag -t $latest_tag -f deployment/Dockerfile ."
        echo "docker push $full_tag"
        echo "docker push $latest_tag"
        return 0
    fi
    
    # Dockerfile 확인
    if [[ ! -f "deployment/Dockerfile" ]]; then
        print_error "Dockerfile을 찾을 수 없습니다: deployment/Dockerfile"
        exit 1
    fi
    
    # 이미지 빌드
    print_info "빌드 중: $full_tag"
    if docker build \
        --tag "$full_tag" \
        --tag "$latest_tag" \
        --file deployment/Dockerfile \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse HEAD)" \
        --build-arg VERSION="$IMAGE_TAG" \
        .; then
        print_success "이미지 빌드 완료"
    else
        print_error "이미지 빌드 실패"
        exit 1
    fi
    
    # 이미지 푸시
    print_step "이미지 푸시 중..."
    docker push "$full_tag"
    docker push "$latest_tag"
    print_success "이미지 푸시 완료"
}

deploy_kubernetes() {
    print_step "Kubernetes 배포 중..."
    
    cd "$PROJECT_ROOT"
    
    # 네임스페이스 생성 (없는 경우)
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -"
    else
        kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    # 시크릿 확인 및 생성
    setup_secrets
    
    # 매니페스트 배포
    local manifest_dir="k8s-gitops/base"
    if [[ ! -d "$manifest_dir" ]]; then
        manifest_dir="k8s"
    fi
    
    if [[ ! -d "$manifest_dir" ]]; then
        print_error "Kubernetes 매니페스트 디렉토리를 찾을 수 없습니다"
        exit 1
    fi
    
    # 이미지 태그 업데이트
    local temp_file=$(mktemp)
    local full_tag="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "sed 's|image: .*blacklist.*|image: $full_tag|g' $manifest_dir/deployment.yaml | kubectl apply -n $NAMESPACE -f -"
        return 0
    fi
    
    # 매니페스트 업데이트 및 적용
    sed "s|image: .*blacklist.*|image: $full_tag|g" "$manifest_dir/deployment.yaml" > "$temp_file"
    
    if kubectl apply -n "$NAMESPACE" -f "$temp_file"; then
        print_success "매니페스트 적용 완료"
    else
        print_error "매니페스트 적용 실패"
        rm -f "$temp_file"
        exit 1
    fi
    
    rm -f "$temp_file"
    
    # 배포 완료 대기
    print_step "배포 완료 대기 중..."
    if kubectl rollout status deployment/blacklist -n "$NAMESPACE" --timeout=300s; then
        print_success "배포 완료"
    else
        print_error "배포 실패"
        exit 1
    fi
}

setup_secrets() {
    print_step "시크릿 설정 중..."
    
    # Registry 시크릿
    if ! kubectl get secret regcred -n "$NAMESPACE" &> /dev/null; then
        if [[ -n "${REGISTRY_USERNAME:-}" && -n "${REGISTRY_PASSWORD:-}" ]]; then
            if [[ "$DRY_RUN" == "true" ]]; then
                echo "kubectl create secret docker-registry regcred --docker-server=$REGISTRY ..."
            else
                kubectl create secret docker-registry regcred \
                    --docker-server="$REGISTRY" \
                    --docker-username="$REGISTRY_USERNAME" \
                    --docker-password="$REGISTRY_PASSWORD" \
                    -n "$NAMESPACE"
                print_success "Registry 시크릿 생성 완료"
            fi
        else
            print_warning "Registry 인증 정보가 없습니다. 수동으로 생성하세요."
        fi
    fi
    
    # 애플리케이션 시크릿
    if ! kubectl get secret blacklist-secrets -n "$NAMESPACE" &> /dev/null; then
        local required_vars=("REGTECH_USERNAME" "REGTECH_PASSWORD" "SECUDIUM_USERNAME" "SECUDIUM_PASSWORD")
        local missing_vars=()
        
        for var in "${required_vars[@]}"; do
            if [[ -z "${!var:-}" ]]; then
                missing_vars+=("$var")
            fi
        done
        
        if [[ ${#missing_vars[@]} -gt 0 ]]; then
            print_warning "다음 환경 변수가 설정되지 않았습니다: ${missing_vars[*]}"
            print_warning "애플리케이션 시크릿을 수동으로 생성하세요."
        else
            if [[ "$DRY_RUN" == "true" ]]; then
                echo "kubectl create secret generic blacklist-secrets ..."
            else
                kubectl create secret generic blacklist-secrets \
                    --from-literal=REGTECH_USERNAME="$REGTECH_USERNAME" \
                    --from-literal=REGTECH_PASSWORD="$REGTECH_PASSWORD" \
                    --from-literal=SECUDIUM_USERNAME="$SECUDIUM_USERNAME" \
                    --from-literal=SECUDIUM_PASSWORD="$SECUDIUM_PASSWORD" \
                    --from-literal=SECRET_KEY="${SECRET_KEY:-k8s-secret-key-$(date +%s)}" \
                    -n "$NAMESPACE"
                print_success "애플리케이션 시크릿 생성 완료"
            fi
        fi
    fi
}

rollback_deployment() {
    print_step "배포 롤백 중..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "kubectl rollout undo deployment/blacklist -n $NAMESPACE"
        return 0
    fi
    
    if kubectl rollout undo deployment/blacklist -n "$NAMESPACE"; then
        kubectl rollout status deployment/blacklist -n "$NAMESPACE" --timeout=300s
        print_success "롤백 완료"
    else
        print_error "롤백 실패"
        exit 1
    fi
}

check_status() {
    print_step "배포 상태 확인 중..."
    
    echo ""
    echo "=== Kubernetes 리소스 ==="
    kubectl get all -n "$NAMESPACE"
    
    echo ""
    echo "=== Pod 상세 상태 ==="
    kubectl get pods -n "$NAMESPACE" -o wide
    
    echo ""
    echo "=== 서비스 엔드포인트 ==="
    kubectl get svc -n "$NAMESPACE"
    
    # Health Check
    local nodeport=$(kubectl get svc blacklist-nodeport -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
    if [[ -n "$nodeport" ]]; then
        echo ""
        echo "=== Health Check ==="
        if curl -s --connect-timeout 5 "http://localhost:$nodeport/health" > /dev/null 2>&1; then
            print_success "애플리케이션 Health Check 성공"
        else
            print_warning "애플리케이션 Health Check 실패"
        fi
        
        echo "Health Check URL: http://localhost:$nodeport/health"
        echo "Application URL: http://localhost:$nodeport"
    fi
}

show_logs() {
    print_step "애플리케이션 로그 확인 중..."
    
    if kubectl get deployment blacklist -n "$NAMESPACE" &> /dev/null; then
        kubectl logs -n "$NAMESPACE" deployment/blacklist --tail=50
        
        echo ""
        echo "실시간 로그를 보려면:"
        echo "kubectl logs -f deployment/blacklist -n $NAMESPACE"
    else
        print_error "blacklist 배포를 찾을 수 없습니다"
    fi
}

cleanup_resources() {
    print_step "리소스 정리 중..."
    
    echo -e "${RED}경고: 이 작업은 $NAMESPACE 네임스페이스의 모든 리소스를 삭제합니다.${NC}"
    if [[ "$DRY_RUN" != "true" ]]; then
        read -p "계속하시겠습니까? (y/N): " confirm
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            echo "정리 작업이 취소되었습니다."
            exit 0
        fi
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "kubectl delete namespace $NAMESPACE"
        return 0
    fi
    
    kubectl delete namespace "$NAMESPACE" --timeout=300s
    print_success "리소스 정리 완료"
}

full_pipeline() {
    print_step "전체 파이프라인 실행 시작..."
    
    run_tests
    build_image
    deploy_kubernetes
    check_status
    
    print_success "전체 파이프라인 완료!"
}

# 메인 실행 로직
main() {
    local command=""
    
    # 인자 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -f|--force)
                FORCE_REBUILD="true"
                shift
                ;;
            -d|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            build|deploy|test|full|rollback|status|logs|cleanup)
                command="$1"
                shift
                ;;
            *)
                print_error "알 수 없는 옵션: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # 명령어 확인
    if [[ -z "$command" ]]; then
        print_error "명령어를 지정해주세요."
        show_usage
        exit 1
    fi
    
    # 환경 설정
    load_environment
    
    # 사전 요구사항 확인
    check_prerequisites
    
    # 설정 출력
    echo ""
    print_info "배포 설정:"
    echo "  명령어: $command"
    echo "  환경: $ENVIRONMENT"
    echo "  네임스페이스: $NAMESPACE"
    echo "  이미지 태그: $IMAGE_TAG"
    echo "  DRY RUN: $DRY_RUN"
    echo ""
    
    # 명령어 실행
    case "$command" in
        build)
            build_image
            ;;
        deploy)
            deploy_kubernetes
            ;;
        test)
            run_tests
            ;;
        full)
            full_pipeline
            ;;
        rollback)
            rollback_deployment
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        cleanup)
            cleanup_resources
            ;;
        *)
            print_error "지원하지 않는 명령어: $command"
            exit 1
            ;;
    esac
    
    print_success "작업 완료!"
}

# 스크립트가 직접 실행된 경우
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi