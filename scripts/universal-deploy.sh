#!/bin/bash

# Universal Deployment Script
# 환경별 설정을 사용한 통합 배포 스크립트

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 도움말 출력
show_help() {
    cat << EOF
Universal Deployment Script

사용법:
    $0 <environment> [options]

환경:
    dev         개발 환경 배포
    staging     스테이징 환경 배포  
    prod        프로덕션 환경 배포

옵션:
    --config-only    설정 검증만 수행
    --dry-run        실제 배포 없이 시뮬레이션
    --force          기존 리소스 강제 덮어쓰기
    --skip-build     이미지 빌드 건너뛰기
    --help           이 도움말 출력

예시:
    $0 prod                    # 프로덕션 배포
    $0 dev --dry-run          # 개발 환경 시뮬레이션
    $0 staging --config-only  # 스테이징 설정 검증

EOF
}

# 환경 검증
validate_environment() {
    local env="$1"
    
    log_info "환경 검증: $env"
    
    # config-manager를 사용한 검증
    if [[ -f "$SCRIPT_DIR/config-manager.sh" ]]; then
        "$SCRIPT_DIR/config-manager.sh" validate "$env"
    else
        log_error "config-manager.sh를 찾을 수 없습니다."
        exit 1
    fi
}

# 설정 초기화
initialize_config() {
    local env="$1"
    
    log_info "설정 초기화: $env"
    
    # config-manager를 사용한 초기화
    "$SCRIPT_DIR/config-manager.sh" init "$env"
}

# Docker 이미지 빌드
build_image() {
    local env="$1"
    local skip_build="$2"
    
    if [[ "$skip_build" == "true" ]]; then
        log_info "이미지 빌드 건너뛰기"
        return 0
    fi
    
    log_info "Docker 이미지 빌드: $env"
    
    # 환경 변수 로드
    source "$PROJECT_ROOT/config/environments/${env}.env"
    
    local image_tag="${IMAGE_TAG:-latest}"
    local full_image="${REGISTRY_URL}/${PROJECT_NAME:-blacklist}:${image_tag}"
    
    log_info "빌드 대상: $full_image"
    
    # Docker 빌드
    if docker build -f "$PROJECT_ROOT/deployment/Dockerfile" -t "$full_image" "$PROJECT_ROOT"; then
        log_success "이미지 빌드 완료: $full_image"
    else
        log_error "이미지 빌드 실패"
        exit 1
    fi
    
    # 레지스트리 푸시 (REGISTRY_USERNAME이 있는 경우)
    if [[ -n "${REGISTRY_USERNAME:-}" ]]; then
        log_info "레지스트리 로그인 및 푸시"
        echo "${REGISTRY_PASSWORD}" | docker login "${REGISTRY_URL}" -u "${REGISTRY_USERNAME}" --password-stdin
        docker push "$full_image"
        log_success "이미지 푸시 완료: $full_image"
    else
        log_info "레지스트리 인증 정보가 없습니다. 로컬 빌드만 수행합니다."
    fi
}

# Kubernetes 배포
deploy_kubernetes() {
    local env="$1"
    local dry_run="$2"
    local force="$3"
    
    log_info "Kubernetes 배포: $env"
    
    # 환경 변수 로드
    source "$PROJECT_ROOT/config/environments/${env}.env"
    
    local dry_run_flag=""
    if [[ "$dry_run" == "true" ]]; then
        dry_run_flag="--dry-run=client"
        log_info "DRY RUN 모드: 실제 리소스 생성 없음"
    fi
    
    # 네임스페이스 생성
    if [[ -f "$PROJECT_ROOT/k8s/rendered/${env}/namespace.yaml" ]]; then
        log_info "네임스페이스 배포"
        kubectl apply -f "$PROJECT_ROOT/k8s/rendered/${env}/namespace.yaml" $dry_run_flag
    fi
    
    # 기본 리소스 배포
    local resources=("service.yaml" "ingress.yaml" "configmap.yaml" "secret.yaml")
    
    for resource in "${resources[@]}"; do
        local resource_file="$PROJECT_ROOT/k8s/rendered/${env}/${resource}"
        if [[ -f "$resource_file" ]]; then
            log_info "배포: $resource"
            kubectl apply -f "$resource_file" $dry_run_flag
        fi
    done
    
    # Helm 차트가 있는 경우 Helm 배포
    if [[ -d "$PROJECT_ROOT/helm" ]]; then
        log_info "Helm 차트 배포"
        
        local helm_values="$PROJECT_ROOT/helm/values-${env}.yaml"
        if [[ ! -f "$helm_values" ]]; then
            helm_values="$PROJECT_ROOT/helm/values.yaml"
        fi
        
        local helm_cmd="helm upgrade --install ${PROJECT_NAME:-blacklist} $PROJECT_ROOT/helm"
        helm_cmd+=" --namespace ${K8S_NAMESPACE:-blacklist}"
        helm_cmd+=" --create-namespace"
        helm_cmd+=" --values $helm_values"
        
        if [[ "$dry_run" == "true" ]]; then
            helm_cmd+=" --dry-run"
        fi
        
        eval "$helm_cmd"
    fi
}

# ArgoCD 배포
deploy_argocd() {
    local env="$1"
    local dry_run="$2"
    
    log_info "ArgoCD 배포: $env"
    
    local argocd_file="$PROJECT_ROOT/argocd/rendered/${env}/application.yaml"
    
    if [[ -f "$argocd_file" ]]; then
        local dry_run_flag=""
        if [[ "$dry_run" == "true" ]]; then
            dry_run_flag="--dry-run=client"
        fi
        
        kubectl apply -f "$argocd_file" $dry_run_flag
        
        # ArgoCD 동기화 (dry-run이 아닌 경우)
        if [[ "$dry_run" != "true" ]] && command -v argocd &> /dev/null; then
            log_info "ArgoCD 애플리케이션 동기화"
            source "$PROJECT_ROOT/config/environments/${env}.env"
            argocd app sync "${PROJECT_NAME:-blacklist}" --grpc-web 2>/dev/null || log_warning "ArgoCD 동기화 실패"
        fi
    else
        log_warning "ArgoCD 설정 파일을 찾을 수 없습니다: $argocd_file"
    fi
}

# 배포 상태 확인
check_deployment() {
    local env="$1"
    
    log_info "배포 상태 확인: $env"
    
    source "$PROJECT_ROOT/config/environments/${env}.env"
    
    echo ""
    echo "📊 배포 상태:"
    echo "   - 네임스페이스: ${K8S_NAMESPACE:-blacklist}"
    echo "   - 환경: $env"
    echo ""
    
    # Pod 상태 확인
    echo "🟢 Pod 상태:"
    kubectl get pods -n "${K8S_NAMESPACE:-blacklist}" 2>/dev/null || echo "   No pods found"
    
    echo ""
    echo "🔗 서비스 상태:"
    kubectl get svc -n "${K8S_NAMESPACE:-blacklist}" 2>/dev/null || echo "   No services found"
    
    echo ""
    echo "🌐 Ingress 상태:"
    kubectl get ingress -n "${K8S_NAMESPACE:-blacklist}" 2>/dev/null || echo "   No ingress found"
    
    echo ""
    echo "🎯 접속 정보:"
    echo "   - 애플리케이션: https://${BASE_DOMAIN}"
    echo "   - ArgoCD: https://${ARGOCD_SERVER}"
    echo ""
}

# 메인 배포 함수
main_deploy() {
    local env="$1"
    local config_only="$2"
    local dry_run="$3"
    local force="$4"
    local skip_build="$5"
    
    log_info "🚀 Universal 배포 시작: $env"
    
    # 1. 환경 검증
    validate_environment "$env"
    
    # 2. 설정 초기화
    initialize_config "$env"
    
    if [[ "$config_only" == "true" ]]; then
        log_success "설정 검증 완료"
        return 0
    fi
    
    # 3. Docker 이미지 빌드
    build_image "$env" "$skip_build"
    
    # 4. Kubernetes 배포
    deploy_kubernetes "$env" "$dry_run" "$force"
    
    # 5. ArgoCD 배포
    deploy_argocd "$env" "$dry_run"
    
    # 6. 배포 상태 확인
    if [[ "$dry_run" != "true" ]]; then
        sleep 5  # 리소스 생성 대기
        check_deployment "$env"
    fi
    
    log_success "🎉 배포 완료: $env"
}

# 메인 로직
main() {
    local environment=""
    local config_only="false"
    local dry_run="false"
    local force="false"
    local skip_build="false"
    
    # 인수 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            dev|staging|prod)
                environment="$1"
                shift
                ;;
            --config-only)
                config_only="true"
                shift
                ;;
            --dry-run)
                dry_run="true"
                shift
                ;;
            --force)
                force="true"
                shift
                ;;
            --skip-build)
                skip_build="true"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 환경 파라미터 확인
    if [[ -z "$environment" ]]; then
        log_error "환경을 지정해주세요 (dev/staging/prod)"
        show_help
        exit 1
    fi
    
    # 배포 실행
    main_deploy "$environment" "$config_only" "$dry_run" "$force" "$skip_build"
}

# 스크립트 실행
main "$@"