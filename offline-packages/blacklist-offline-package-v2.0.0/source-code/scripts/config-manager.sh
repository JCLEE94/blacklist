#!/bin/bash

# Configuration Manager Script
# 환경별 설정을 관리하고 템플릿을 렌더링하는 스크립트

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_ROOT/config"

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
Configuration Manager Script

사용법:
    $0 <command> [options]

Commands:
    init <env>              환경 초기화 (dev, staging, prod)
    validate <env>          환경 설정 검증
    render <env> <template> 템플릿 렌더링
    deploy <env>            환경별 배포
    list                    사용 가능한 환경 목록 출력
    backup <env>            환경 설정 백업
    restore <env> <backup>  환경 설정 복원

Examples:
    $0 init prod
    $0 validate dev
    $0 render prod k8s/deployment.yaml
    $0 deploy staging
    $0 list

EOF
}

# 환경 파일 로드
load_environment() {
    local env="$1"
    local env_file="$CONFIG_DIR/environments/${env}.env"
    
    if [[ ! -f "$env_file" ]]; then
        log_error "환경 파일을 찾을 수 없습니다: $env_file"
        exit 1
    fi
    
    log_info "환경 로드 중: $env"
    
    # 환경 변수 로드
    set -a
    source "$env_file"
    set +a
    
    log_success "환경 변수 로드 완료: $env"
}

# 필수 환경 변수 검증
validate_environment() {
    local env="$1"
    local missing_vars=()
    
    load_environment "$env"
    
    log_info "환경 검증 중: $env"
    
    # 필수 변수 목록
    local required_vars=(
        "BASE_DOMAIN"
        "REGISTRY_URL"
        "GIT_REPOSITORY"
        "GIT_USERNAME"
        "GIT_EMAIL"
    )
    
    # 필수 변수 검사
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "누락된 필수 환경 변수:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
    
    log_success "환경 검증 완료: $env"
}

# 템플릿 렌더링
render_template() {
    local env="$1"
    local template_path="$2"
    local output_path="${3:-}"
    
    load_environment "$env"
    
    if [[ ! -f "$template_path" ]]; then
        log_error "템플릿 파일을 찾을 수 없습니다: $template_path"
        exit 1
    fi
    
    log_info "템플릿 렌더링: $template_path"
    
    # envsubst를 사용한 템플릿 렌더링
    if [[ -n "$output_path" ]]; then
        mkdir -p "$(dirname "$output_path")"
        envsubst < "$template_path" > "$output_path"
        log_success "렌더링 완료: $output_path"
    else
        envsubst < "$template_path"
    fi
}

# 환경 초기화
init_environment() {
    local env="$1"
    
    log_info "환경 초기화: $env"
    
    # 환경 검증
    validate_environment "$env"
    
    # 필요한 디렉토리 생성
    local dirs=(
        "$PROJECT_ROOT/k8s/rendered/$env"
        "$PROJECT_ROOT/helm/rendered/$env"
        "$PROJECT_ROOT/deployment/rendered/$env"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_info "디렉토리 생성: $dir"
    done
    
    # 기본 템플릿 렌더링
    if [[ -f "$PROJECT_ROOT/k8s/deployment.yaml.template" ]]; then
        render_template "$env" "$PROJECT_ROOT/k8s/deployment.yaml.template" "$PROJECT_ROOT/k8s/rendered/$env/deployment.yaml"
    fi
    
    if [[ -f "$PROJECT_ROOT/k8s/service.yaml.template" ]]; then
        render_template "$env" "$PROJECT_ROOT/k8s/service.yaml.template" "$PROJECT_ROOT/k8s/rendered/$env/service.yaml"
    fi
    
    log_success "환경 초기화 완료: $env"
}

# 환경 목록 출력
list_environments() {
    log_info "사용 가능한 환경:"
    
    for env_file in "$CONFIG_DIR/environments"/*.env; do
        if [[ -f "$env_file" ]]; then
            local env_name=$(basename "$env_file" .env)
            echo "  - $env_name"
        fi
    done
}

# 환경 설정 백업
backup_environment() {
    local env="$1"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_dir="$CONFIG_DIR/backups/$env"
    local backup_file="$backup_dir/backup_${timestamp}.tar.gz"
    
    log_info "환경 설정 백업: $env"
    
    mkdir -p "$backup_dir"
    
    # 환경 파일과 렌더링된 파일들 백업
    tar -czf "$backup_file" \
        -C "$PROJECT_ROOT" \
        "config/environments/${env}.env" \
        "k8s/rendered/$env" \
        "helm/rendered/$env" \
        "deployment/rendered/$env" \
        2>/dev/null || true
    
    log_success "백업 완료: $backup_file"
    echo "$backup_file"
}

# 환경 설정 복원
restore_environment() {
    local env="$1"
    local backup_file="$2"
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "백업 파일을 찾을 수 없습니다: $backup_file"
        exit 1
    fi
    
    log_info "환경 설정 복원: $env"
    log_warning "기존 설정이 덮어씌워집니다. 계속하시겠습니까? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        tar -xzf "$backup_file" -C "$PROJECT_ROOT"
        log_success "복원 완료: $env"
    else
        log_info "복원이 취소되었습니다."
    fi
}

# 환경별 배포
deploy_environment() {
    local env="$1"
    
    log_info "환경 배포: $env"
    
    # 환경 검증
    validate_environment "$env"
    
    # 환경 초기화
    init_environment "$env"
    
    # ArgoCD 배포 스크립트 실행
    if [[ -f "$PROJECT_ROOT/scripts/deploy.sh" ]]; then
        log_info "ArgoCD 배포 실행"
        ENVIRONMENT="$env" "$PROJECT_ROOT/scripts/deploy.sh"
    else
        log_warning "배포 스크립트를 찾을 수 없습니다: $PROJECT_ROOT/scripts/deploy.sh"
    fi
    
    log_success "환경 배포 완료: $env"
}

# 메인 로직
main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        init)
            if [[ $# -ne 1 ]]; then
                log_error "사용법: $0 init <env>"
                exit 1
            fi
            init_environment "$1"
            ;;
        validate)
            if [[ $# -ne 1 ]]; then
                log_error "사용법: $0 validate <env>"
                exit 1
            fi
            validate_environment "$1"
            ;;
        render)
            if [[ $# -lt 2 ]]; then
                log_error "사용법: $0 render <env> <template> [output]"
                exit 1
            fi
            render_template "$1" "$2" "${3:-}"
            ;;
        deploy)
            if [[ $# -ne 1 ]]; then
                log_error "사용법: $0 deploy <env>"
                exit 1
            fi
            deploy_environment "$1"
            ;;
        list)
            list_environments
            ;;
        backup)
            if [[ $# -ne 1 ]]; then
                log_error "사용법: $0 backup <env>"
                exit 1
            fi
            backup_environment "$1"
            ;;
        restore)
            if [[ $# -ne 2 ]]; then
                log_error "사용법: $0 restore <env> <backup_file>"
                exit 1
            fi
            restore_environment "$1" "$2"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "알 수 없는 명령: $command"
            show_help
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"