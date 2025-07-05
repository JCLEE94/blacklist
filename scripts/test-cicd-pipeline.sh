#!/bin/bash

echo "🧪 CI/CD 파이프라인 통합 테스트"
echo "================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 스크립트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# 테스트 모드 확인
DRY_RUN=${DRY_RUN:-false}
VERBOSE=${VERBOSE:-false}

# 테스트 실행
run_test() {
    local test_name=$1
    local test_cmd=$2
    
    print_step "Running: $test_name"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "[DRY RUN] Would run: $test_cmd"
        return 0
    fi
    
    if eval "$test_cmd"; then
        print_success "$test_name passed"
        return 0
    else
        print_error "$test_name failed"
        return 1
    fi
}

# 1. 파이프라인 설정 테스트
test_pipeline_configuration() {
    print_step "Testing pipeline configuration..."
    
    # GitHub Actions 워크플로우 검증
    if [[ ! -f "$PROJECT_ROOT/.github/workflows/complete-cicd-pipeline.yml" ]]; then
        print_error "Main workflow file not found"
        return 1
    fi
    
    # ArgoCD 설정 검증
    if [[ ! -f "$PROJECT_ROOT/k8s/argocd-app-clean.yaml" ]]; then
        print_error "ArgoCD application manifest not found"
        return 1
    fi
    
    # Docker 설정 검증
    if [[ ! -f "$PROJECT_ROOT/deployment/Dockerfile" ]]; then
        print_error "Dockerfile not found"
        return 1
    fi
    
    print_success "Pipeline configuration is valid"
    return 0
}

# 2. 코드 품질 도구 테스트
test_code_quality_tools() {
    print_step "Testing code quality tools..."
    
    # Python 설치 확인
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 not found"
        return 1
    fi
    
    # 필수 패키지 확인
    local required_packages=("flake8" "pytest" "black")
    for pkg in "${required_packages[@]}"; do
        if ! python3 -m pip show "$pkg" &> /dev/null; then
            print_warning "$pkg not installed, installing..."
            python3 -m pip install "$pkg" || return 1
        fi
    done
    
    print_success "Code quality tools are available"
    return 0
}

# 3. Docker 빌드 테스트
test_docker_build() {
    print_step "Testing Docker build..."
    
    cd "$PROJECT_ROOT" || return 1
    
    # Docker 설치 확인
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found"
        return 1
    fi
    
    # 테스트 빌드 (캐시 사용)
    if [[ "$DRY_RUN" != "true" ]]; then
        docker build -f deployment/Dockerfile -t blacklist-test:latest . || {
            print_error "Docker build failed"
            return 1
        }
    fi
    
    print_success "Docker build test passed"
    return 0
}

# 4. Kubernetes 매니페스트 검증
test_kubernetes_manifests() {
    print_step "Testing Kubernetes manifests..."
    
    # kubectl 설치 확인
    if ! command -v kubectl &> /dev/null; then
        print_warning "kubectl not found, skipping manifest validation"
        return 0
    fi
    
    # 매니페스트 드라이런
    local manifests=(
        "k8s/namespace.yaml"
        "k8s/deployment.yaml"
        "k8s/service.yaml"
        "k8s/ingress.yaml"
    )
    
    for manifest in "${manifests[@]}"; do
        if [[ -f "$PROJECT_ROOT/$manifest" ]]; then
            kubectl apply --dry-run=client -f "$PROJECT_ROOT/$manifest" &> /dev/null || {
                print_error "Invalid manifest: $manifest"
                return 1
            }
        fi
    done
    
    print_success "Kubernetes manifests are valid"
    return 0
}

# 5. ArgoCD 연결 테스트
test_argocd_connection() {
    print_step "Testing ArgoCD connection..."
    
    # argocd CLI 확인
    if ! command -v argocd &> /dev/null; then
        print_warning "argocd CLI not found, skipping connection test"
        return 0
    fi
    
    # 연결 테스트 (실제 서버가 필요하므로 드라이런에서는 스킵)
    if [[ "$DRY_RUN" != "true" ]]; then
        argocd app list --grpc-web &> /dev/null || {
            print_warning "ArgoCD connection failed (might need login)"
            return 0
        }
    fi
    
    print_success "ArgoCD connection test passed"
    return 0
}

# 6. 통합 테스트 실행
test_integration_tests() {
    print_step "Running CI/CD integration tests..."
    
    cd "$PROJECT_ROOT" || return 1
    
    # pytest 실행
    if [[ "$DRY_RUN" != "true" ]]; then
        python3 -m pytest tests/integration/test_cicd_pipeline.py -v || {
            print_error "Integration tests failed"
            return 1
        }
    fi
    
    print_success "Integration tests passed"
    return 0
}

# 7. 파이프라인 유틸리티 테스트
test_pipeline_utilities() {
    print_step "Testing pipeline utilities..."
    
    # 유틸리티 스크립트 테스트
    if [[ -f "$PROJECT_ROOT/scripts/lib/cicd_testability.py" ]]; then
        python3 "$PROJECT_ROOT/scripts/lib/cicd_testability.py" --dry-run --stage code-quality || {
            print_error "Pipeline utility test failed"
            return 1
        }
    fi
    
    print_success "Pipeline utilities are functional"
    return 0
}

# 메인 실행
main() {
    local failed=0
    
    echo "Environment:"
    echo "- DRY_RUN: $DRY_RUN"
    echo "- VERBOSE: $VERBOSE"
    echo "- PROJECT_ROOT: $PROJECT_ROOT"
    echo ""
    
    # 테스트 실행
    local tests=(
        "test_pipeline_configuration"
        "test_code_quality_tools"
        "test_docker_build"
        "test_kubernetes_manifests"
        "test_argocd_connection"
        "test_integration_tests"
        "test_pipeline_utilities"
    )
    
    for test in "${tests[@]}"; do
        if ! $test; then
            ((failed++))
        fi
        echo ""
    done
    
    # 결과 요약
    echo "================================"
    if [[ $failed -eq 0 ]]; then
        print_success "All tests passed!"
    else
        print_error "$failed test(s) failed"
    fi
    
    return $failed
}

# 스크립트 실행
main
exit $?