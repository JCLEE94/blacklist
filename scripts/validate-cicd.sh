#!/bin/bash

# CI/CD 파이프라인 검증 스크립트
# GitHub Actions, GHCR, ArgoCD 통합 테스트

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 설정
GITHUB_REPO="JCLEE94/blacklist"
GHCR_IMAGE="ghcr.io/jclee94/blacklist"
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"
APP_NAME="blacklist"
NAMESPACE="blacklist"

# 결과 저장
RESULTS=()
FAILURES=()

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    RESULTS+=("✓ $1")
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    FAILURES+=("✗ $1")
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${PURPLE}ℹ${NC} $1"
}

# 1. 환경 변수 검증
check_environment() {
    print_header "환경 변수 검증"
    
    local required_vars=(
        "GITHUB_USERNAME"
        "GITHUB_TOKEN"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -eq 0 ]; then
        print_success "모든 필수 환경 변수가 설정됨"
    else
        print_error "다음 환경 변수가 누락됨: ${missing_vars[*]}"
        echo "  source scripts/load-env.sh 실행 필요"
        return 1
    fi
}

# 2. GitHub Actions 워크플로우 검증
check_github_actions() {
    print_header "GitHub Actions 워크플로우 검증"
    
    # GitHub CLI 설치 확인
    if ! command -v gh &> /dev/null; then
        print_warning "GitHub CLI가 설치되지 않음. 수동 확인 필요"
        echo "  https://github.com/$GITHUB_REPO/actions"
        return
    fi
    
    # 최근 워크플로우 실행 확인
    print_info "최근 워크플로우 실행 상태 확인 중..."
    
    local workflow_status=$(gh run list --repo $GITHUB_REPO --limit 1 --json status,conclusion,name,headBranch 2>/dev/null || echo "error")
    
    if [ "$workflow_status" != "error" ]; then
        echo "$workflow_status" | jq -r '.[] | "- \(.name): \(.status) (\(.conclusion // "running"))"'
        
        # 실행 중이거나 성공한 워크플로우가 있는지 확인
        if echo "$workflow_status" | jq -e '.[0].conclusion == "success"' &>/dev/null; then
            print_success "최근 워크플로우 실행 성공"
        else
            print_warning "최근 워크플로우 확인 필요"
        fi
    else
        print_warning "GitHub API 접근 실패. 웹에서 확인 필요"
    fi
}

# 3. GHCR 이미지 확인
check_ghcr_images() {
    print_header "GitHub Container Registry 이미지 검증"
    
    # Docker 로그인 상태 확인
    if docker info 2>/dev/null | grep -q "Username: ${GITHUB_USERNAME}"; then
        print_success "Docker가 GHCR에 로그인됨"
    else
        print_info "GHCR 로그인 시도 중..."
        echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USERNAME" --password-stdin
    fi
    
    # 이미지 존재 확인
    print_info "GHCR 이미지 확인 중: $GHCR_IMAGE"
    
    if docker manifest inspect "$GHCR_IMAGE:latest" &>/dev/null; then
        print_success "최신 이미지가 GHCR에 존재함"
        
        # 이미지 메타데이터 확인
        local image_created=$(docker inspect "$GHCR_IMAGE:latest" 2>/dev/null | jq -r '.[0].Created' || echo "unknown")
        if [ "$image_created" != "unknown" ]; then
            print_info "이미지 생성 시간: $image_created"
        fi
    else
        print_error "GHCR에서 이미지를 찾을 수 없음"
    fi
    
    # 이미지 태그 목록
    print_info "사용 가능한 태그 확인 중..."
    # GitHub API를 통한 태그 확인 (packages API는 인증 필요)
    curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
        "https://api.github.com/users/jclee94/packages/container/blacklist/versions" 2>/dev/null | \
        jq -r '.[] | .metadata.container.tags[]' 2>/dev/null | head -5 || \
        print_warning "태그 목록을 가져올 수 없음"
}

# 4. Kubernetes 클러스터 연결 확인
check_kubernetes() {
    print_header "Kubernetes 클러스터 검증"
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl이 설치되지 않음"
        return 1
    fi
    
    if kubectl cluster-info &>/dev/null; then
        print_success "Kubernetes 클러스터에 연결됨"
        
        # 네임스페이스 확인
        if kubectl get namespace $NAMESPACE &>/dev/null; then
            print_success "네임스페이스 '$NAMESPACE' 존재"
        else
            print_error "네임스페이스 '$NAMESPACE'가 존재하지 않음"
        fi
        
        # GHCR 시크릿 확인
        if kubectl get secret ghcr-secret -n $NAMESPACE &>/dev/null; then
            print_success "GHCR 시크릿이 구성됨"
        else
            print_error "GHCR 시크릿이 없음"
            echo "  ./scripts/setup-ghcr-secret.sh 실행 필요"
        fi
    else
        print_error "Kubernetes 클러스터에 연결할 수 없음"
        return 1
    fi
}

# 5. ArgoCD 상태 확인
check_argocd() {
    print_header "ArgoCD 검증"
    
    if ! command -v argocd &> /dev/null; then
        print_error "ArgoCD CLI가 설치되지 않음"
        return 1
    fi
    
    # ArgoCD 로그인 확인
    if argocd account whoami --grpc-web &>/dev/null; then
        print_success "ArgoCD에 로그인됨"
        
        # 애플리케이션 상태 확인
        if argocd app get $APP_NAME --grpc-web &>/dev/null; then
            print_success "ArgoCD 애플리케이션 '$APP_NAME'이 존재함"
            
            # 동기화 상태 확인
            local sync_status=$(argocd app get $APP_NAME --grpc-web -o json | jq -r '.status.sync.status')
            local health_status=$(argocd app get $APP_NAME --grpc-web -o json | jq -r '.status.health.status')
            
            print_info "동기화 상태: $sync_status"
            print_info "헬스 상태: $health_status"
            
            if [ "$sync_status" == "Synced" ]; then
                print_success "애플리케이션이 동기화됨"
            else
                print_warning "애플리케이션 동기화 필요"
            fi
            
            if [ "$health_status" == "Healthy" ]; then
                print_success "애플리케이션이 정상 상태"
            else
                print_warning "애플리케이션 헬스 확인 필요"
            fi
        else
            print_error "ArgoCD 애플리케이션을 찾을 수 없음"
            echo "  ./scripts/setup/argocd-cli-setup.sh 실행 필요"
        fi
    else
        print_error "ArgoCD에 로그인되지 않음"
        echo "  argocd login $ARGOCD_SERVER --grpc-web"
    fi
}

# 6. 배포된 애플리케이션 확인
check_deployment() {
    print_header "배포된 애플리케이션 검증"
    
    # Pod 상태 확인
    local pod_count=$(kubectl get pods -n $NAMESPACE -l app=blacklist --no-headers 2>/dev/null | wc -l)
    if [ "$pod_count" -gt 0 ]; then
        print_success "$pod_count개의 Pod이 실행 중"
        
        # Pod 상태 상세
        kubectl get pods -n $NAMESPACE -l app=blacklist
        
        # 실행 중인 이미지 확인
        local running_image=$(kubectl get pods -n $NAMESPACE -l app=blacklist -o jsonpath='{.items[0].spec.containers[0].image}' 2>/dev/null)
        if [ -n "$running_image" ]; then
            print_info "실행 중인 이미지: $running_image"
        fi
    else
        print_error "실행 중인 Pod이 없음"
    fi
    
    # 서비스 엔드포인트 확인
    if kubectl get service blacklist -n $NAMESPACE &>/dev/null; then
        print_success "서비스가 존재함"
        
        # 헬스 체크
        local pod_name=$(kubectl get pod -n $NAMESPACE -l app=blacklist -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [ -n "$pod_name" ]; then
            print_info "헬스 체크 수행 중..."
            if kubectl exec -n $NAMESPACE "$pod_name" -- curl -s http://localhost:2541/health | grep -q "healthy"; then
                print_success "애플리케이션 헬스 체크 통과"
            else
                print_error "애플리케이션 헬스 체크 실패"
            fi
        fi
    else
        print_error "서비스를 찾을 수 없음"
    fi
}

# 7. 엔드투엔드 파이프라인 테스트
test_e2e_pipeline() {
    print_header "엔드투엔드 파이프라인 테스트"
    
    echo -e "${YELLOW}이 테스트는 실제 커밋을 생성하고 파이프라인을 트리거합니다.${NC}"
    echo -n "계속하시겠습니까? (y/n): "
    read -r confirm
    
    if [[ "$confirm" != "y" ]]; then
        print_warning "E2E 테스트가 건너뛰어짐"
        return
    fi
    
    # 테스트 파일 생성
    local test_file="test-cicd-$(date +%Y%m%d-%H%M%S).txt"
    echo "CI/CD Pipeline Test - $(date)" > "$test_file"
    
    # Git 커밋 및 푸시
    git add "$test_file"
    git commit -m "test: CI/CD pipeline validation - $(date +%Y%m%d-%H%M%S)"
    git push origin main
    
    print_info "파이프라인이 트리거되었습니다."
    print_info "진행 상황 확인: https://github.com/$GITHUB_REPO/actions"
    
    # 테스트 파일 정리
    rm -f "$test_file"
    git rm "$test_file" &>/dev/null || true
    git commit -m "chore: cleanup test file" &>/dev/null || true
}

# 8. 결과 요약
print_summary() {
    print_header "검증 결과 요약"
    
    echo -e "\n${GREEN}성공 항목:${NC}"
    for result in "${RESULTS[@]}"; do
        echo "  $result"
    done
    
    if [ ${#FAILURES[@]} -gt 0 ]; then
        echo -e "\n${RED}실패 항목:${NC}"
        for failure in "${FAILURES[@]}"; do
            echo "  $failure"
        done
        
        echo -e "\n${YELLOW}권장 조치사항:${NC}"
        echo "1. 환경 변수 설정 확인: source scripts/load-env.sh"
        echo "2. GHCR 시크릿 설정: ./scripts/setup-ghcr-secret.sh"
        echo "3. ArgoCD 설정: ./scripts/setup/argocd-cli-setup.sh"
        echo "4. GitHub Actions Secrets 확인"
    else
        echo -e "\n${GREEN}모든 검증을 통과했습니다! 🎉${NC}"
    fi
    
    # 검증 보고서 저장
    local report_file="cicd-validation-report-$(date +%Y%m%d-%H%M%S).txt"
    {
        echo "CI/CD Pipeline Validation Report"
        echo "Generated: $(date)"
        echo "================================"
        echo ""
        echo "Success Items:"
        printf '%s\n' "${RESULTS[@]}"
        echo ""
        if [ ${#FAILURES[@]} -gt 0 ]; then
            echo "Failed Items:"
            printf '%s\n' "${FAILURES[@]}"
        fi
    } > "$report_file"
    
    print_info "검증 보고서가 $report_file에 저장되었습니다."
}

# 메인 실행
main() {
    echo -e "${BLUE}CI/CD 파이프라인 검증을 시작합니다...${NC}"
    echo "================================"
    
    # 검증 단계 실행
    check_environment || true
    check_github_actions || true
    check_ghcr_images || true
    check_kubernetes || true
    check_argocd || true
    check_deployment || true
    
    # E2E 테스트 (선택적)
    # test_e2e_pipeline || true
    
    # 결과 요약
    print_summary
}

# 스크립트 실행
main "$@"