#!/bin/bash
#
# GitOps 완전 동기화 스크립트
# Blacklist 프로젝트 CI/CD 파이프라인 강제 트리거
#

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
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

# 설정
REGISTRY="registry.jclee.me"
IMAGE_NAME="jclee94/blacklist"
HELM_CHART_NAME="blacklist"
ARGOCD_URL="https://argo.jclee.me"
GITHUB_REPO="JCLEE94/blacklist"

# 환경 변수 확인
check_prerequisites() {
    log_info "전제 조건 확인 중..."
    
    local missing_deps=()
    
    # 필수 명령어 확인
    for cmd in git curl jq helm kubectl; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "다음 명령어들이 필요합니다: ${missing_deps[*]}"
        exit 1
    fi
    
    # 환경 변수 확인
    local missing_vars=()
    for var in ARGOCD_TOKEN GITHUB_TOKEN; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_warning "다음 환경 변수가 설정되지 않음: ${missing_vars[*]}"
        log_warning "일부 기능이 제한될 수 있습니다."
    fi
    
    log_success "전제 조건 확인 완료"
}

# Git 상태 확인
check_git_status() {
    log_info "Git 상태 확인 중..."
    
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Git 리포지터리가 아닙니다."
        exit 1
    fi
    
    # 현재 브랜치 확인
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    log_info "현재 브랜치: $current_branch"
    
    # 변경사항 확인
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "커밋되지 않은 변경사항이 있습니다:"
        git status --short
    fi
    
    # 원격과의 차이 확인
    local ahead_behind
    ahead_behind=$(git rev-list --left-right --count origin/$current_branch...$current_branch 2>/dev/null || echo "0	0")
    local ahead=$(echo "$ahead_behind" | cut -f1)
    local behind=$(echo "$ahead_behind" | cut -f2)
    
    if [ "$behind" -gt 0 ]; then
        log_warning "로컬이 원격보다 $behind 커밋 뒤처져 있습니다."
        log_info "git pull을 실행하는 것을 고려해보세요."
    fi
    
    if [ "$ahead" -gt 0 ]; then
        log_info "로컬이 원격보다 $ahead 커밋 앞서 있습니다."
    fi
    
    log_success "Git 상태 확인 완료"
}

# CI/CD 트리거 커밋 생성
create_trigger_commit() {
    log_info "CI/CD 트리거 커밋 생성 중..."
    
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # .gitops_sync 파일 업데이트
    echo "$timestamp: CI/CD sync trigger" >> .gitops_sync
    
    # 트리거 커밋 생성
    git add .gitops_sync
    git commit -m "cicd: trigger ArgoCD sync with GitHub Actions pipeline

🚀 CI/CD 완전 동기화:
1. GitHub Actions 워크플로우 강제 실행
2. Docker 이미지 빌드 및 푸시 → $REGISTRY
3. Helm 차트 패키징 → charts.jclee.me  
4. ArgoCD 애플리케이션 자동 동기화
5. Kubernetes 롤링 업데이트 실행
6. 제로 다운타임 배포 완료

Target: $REGISTRY/$IMAGE_NAME:latest
Chart: charts.jclee.me/$HELM_CHART_NAME v3.2.10+
ArgoCD: $ARGOCD_URL/applications/$HELM_CHART_NAME

🤖 Generated with GitOps Sync Script"
    
    log_success "트리거 커밋 생성 완료"
}

# GitHub Actions 트리거
trigger_github_actions() {
    log_info "GitHub Actions 워크플로우 트리거 중..."
    
    # Git push로 워크플로우 트리거
    if git push origin main; then
        log_success "GitHub push 완료 - CI/CD 파이프라인 시작됨"
    else
        log_error "GitHub push 실패"
        return 1
    fi
    
    # GitHub CLI가 있으면 워크플로우 상태 모니터링
    if command -v gh &> /dev/null && [ -n "${GITHUB_TOKEN:-}" ]; then
        log_info "GitHub Actions 워크플로우 상태 모니터링 중..."
        
        # 잠시 대기 후 워크플로우 확인
        sleep 10
        
        local run_status
        run_status=$(gh run list --repo "$GITHUB_REPO" --limit 1 --json status,conclusion,workflowName --jq '.[0]')
        
        if [ "$run_status" != "null" ]; then
            local workflow_name
            local status
            workflow_name=$(echo "$run_status" | jq -r '.workflowName')
            status=$(echo "$run_status" | jq -r '.status')
            
            log_info "워크플로우: $workflow_name"
            log_info "상태: $status"
            
            # 실시간 모니터링 제안
            echo ""
            log_info "실시간 로그 모니터링: gh run watch --repo $GITHUB_REPO"
            echo ""
        fi
    else
        log_warning "GitHub CLI 없음 - 수동으로 워크플로우 상태를 확인하세요:"
        log_warning "https://github.com/$GITHUB_REPO/actions"
    fi
}

# ArgoCD 상태 확인
check_argocd_status() {
    log_info "ArgoCD 애플리케이션 상태 확인 중..."
    
    if [ -z "${ARGOCD_TOKEN:-}" ]; then
        log_warning "ARGOCD_TOKEN이 설정되지 않음 - ArgoCD 상태 확인 건너뛰기"
        return 0
    fi
    
    # ArgoCD API 호출
    local app_status
    if app_status=$(curl -s -k -H "Authorization: Bearer $ARGOCD_TOKEN" \
                    "$ARGOCD_URL/api/v1/applications/$HELM_CHART_NAME" 2>/dev/null); then
        
        local sync_status
        local health_status
        sync_status=$(echo "$app_status" | jq -r '.status.sync.status // "Unknown"')
        health_status=$(echo "$app_status" | jq -r '.status.health.status // "Unknown"')
        
        log_info "ArgoCD 동기화 상태: $sync_status"
        log_info "ArgoCD 헬스 상태: $health_status"
        
        if [ "$sync_status" = "OutOfSync" ]; then
            log_warning "ArgoCD 애플리케이션이 동기화되지 않음"
            log_info "수동 동기화가 필요할 수 있습니다"
        fi
        
    else
        log_warning "ArgoCD API 호출 실패 - 수동으로 상태를 확인하세요:"
        log_warning "$ARGOCD_URL/applications/$HELM_CHART_NAME"
    fi
}

# Docker 레지스트리 상태 확인
check_docker_registry() {
    log_info "Docker 레지스트리 상태 확인 중..."
    
    # 레지스트리 접근 확인
    if curl -s -f "$REGISTRY/v2/" > /dev/null; then
        log_success "Docker 레지스트리 접근 가능: $REGISTRY"
        
        # 최근 태그 확인 (선택적)
        local tags_response
        if tags_response=$(curl -s "$REGISTRY/v2/$IMAGE_NAME/tags/list" 2>/dev/null); then
            local latest_tags
            latest_tags=$(echo "$tags_response" | jq -r '.tags[]? | select(. != null)' | head -5 | tr '\n' ' ')
            if [ -n "$latest_tags" ]; then
                log_info "최근 이미지 태그: $latest_tags"
            fi
        fi
    else
        log_warning "Docker 레지스트리 접근 불가: $REGISTRY"
    fi
}

# 배포 후 헬스 체크
health_check() {
    log_info "애플리케이션 헬스 체크 실행 중..."
    
    # 로컬 Docker 컨테이너 확인
    if curl -s -f "http://localhost:32542/health" > /dev/null 2>&1; then
        log_success "로컬 애플리케이션 정상 동작 (포트 32542)"
        
        local health_response
        health_response=$(curl -s "http://localhost:32542/health" | jq '.' 2>/dev/null || echo "Health OK")
        log_info "헬스 상태: $health_response"
    else
        log_warning "로컬 애플리케이션 접근 불가 (포트 32542)"
        log_info "Docker 컨테이너가 실행 중인지 확인하세요: docker-compose ps"
    fi
}

# 성능 벤치마크
performance_benchmark() {
    log_info "간단한 성능 벤치마크 실행 중..."
    
    if curl -s -f "http://localhost:32542/api/blacklist/active" > /dev/null 2>&1; then
        local response_time
        response_time=$(curl -w "%{time_total}" -s -o /dev/null "http://localhost:32542/api/blacklist/active")
        log_info "API 응답 시간: ${response_time}s"
        
        # 성능 임계값 확인
        if (( $(echo "$response_time < 0.1" | bc -l) )); then
            log_success "우수한 성능 (<100ms)"
        elif (( $(echo "$response_time < 0.5" | bc -l) )); then
            log_success "양호한 성능 (<500ms)"
        else
            log_warning "성능 개선 필요 (>${response_time}s)"
        fi
    else
        log_warning "성능 벤치마크 실행 불가 - API 엔드포인트 접근 실패"
    fi
}

# 배포 상태 리포트 생성
generate_deployment_report() {
    log_info "배포 상태 리포트 생성 중..."
    
    local report_file="deployment-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# 🚀 Blacklist CI/CD GitOps 배포 리포트

**생성 시간**: $(date)
**리포지터리**: $GITHUB_REPO
**트리거 방법**: GitOps 동기화 스크립트

## 📊 파이프라인 상태

### GitHub Actions
- **워크플로우**: CI/CD Pipeline
- **트리거**: Git Push to main branch
- **상태**: GitHub Actions에서 확인 필요
- **링크**: https://github.com/$GITHUB_REPO/actions

### Docker Registry
- **레지스트리**: $REGISTRY
- **이미지**: $IMAGE_NAME:latest
- **상태**: $(curl -s -f "$REGISTRY/v2/" > /dev/null && echo "✅ 접근 가능" || echo "⚠️ 접근 확인 필요")

### Helm Chart
- **차트**: $HELM_CHART_NAME
- **버전**: 3.2.10+
- **리포지터리**: charts.jclee.me

### ArgoCD
- **애플리케이션**: $HELM_CHART_NAME
- **URL**: $ARGOCD_URL/applications/$HELM_CHART_NAME
- **동기화**: 자동 동기화 활성화됨

## 🔍 애플리케이션 상태

### 로컬 컨테이너 (Docker Compose)
- **포트**: 32542
- **상태**: $(curl -s -f "http://localhost:32542/health" > /dev/null && echo "✅ 정상" || echo "⚠️ 확인 필요")
- **헬스 체크**: http://localhost:32542/health

### API 엔드포인트
- **블랙리스트 API**: $(curl -s -f "http://localhost:32542/api/blacklist/active" > /dev/null && echo "✅ 정상" || echo "⚠️ 확인 필요")
- **FortiGate API**: $(curl -s -f "http://localhost:32542/api/fortigate" > /dev/null && echo "✅ 정상" || echo "⚠️ 확인 필요")

## 📈 성능 메트릭

### 응답 시간
- **API 응답**: $(curl -w "%{time_total}s" -s -o /dev/null "http://localhost:32542/api/blacklist/active" 2>/dev/null || echo "측정 불가")
- **목표**: <100ms (우수), <500ms (양호)

### 리소스 사용률
- **메모리**: Docker stats에서 확인
- **CPU**: Docker stats에서 확인

## 🔄 다음 단계

1. **GitHub Actions 모니터링**
   \`\`\`bash
   gh run watch --repo $GITHUB_REPO
   \`\`\`

2. **ArgoCD 동기화 확인**
   - ArgoCD UI에서 애플리케이션 상태 확인
   - 필요시 수동 동기화 실행

3. **Kubernetes 배포 확인** (프로덕션)
   \`\`\`bash
   kubectl get pods -l app=blacklist -n blacklist
   kubectl rollout status deployment/blacklist -n blacklist
   \`\`\`

4. **엔드포인트 테스트**
   \`\`\`bash
   curl https://blacklist.jclee.me/health
   curl https://blacklist.jclee.me/api/blacklist/active
   \`\`\`

## 🚨 문제 해결

### GitHub Actions 실패 시
- 워크플로우 로그 확인
- 시크릿 설정 확인 (REGISTRY_*, ARGOCD_TOKEN, KUBE_CONFIG)

### ArgoCD 동기화 실패 시
- 애플리케이션 상태 확인
- Helm 차트 문법 검증
- 수동 동기화 실행

### 컨테이너 실행 실패 시
- Docker 로그 확인: \`docker-compose logs -f\`
- 포트 충돌 확인: \`lsof -i :32542\`
- 이미지 업데이트: \`docker-compose pull && docker-compose up -d\`

---
**리포트 생성 시간**: $(date)
EOF
    
    log_success "배포 리포트 생성 완료: $report_file"
    echo ""
    echo "=== 배포 리포트 미리보기 ==="
    head -30 "$report_file"
    echo "... (전체 리포트는 $report_file 파일 참조)"
    echo ""
}

# 메인 실행 함수
main() {
    echo ""
    echo "🚀 Blacklist GitOps 완전 동기화 스크립트"
    echo "=============================================="
    echo ""
    
    # 모든 단계 실행
    check_prerequisites
    echo ""
    
    check_git_status
    echo ""
    
    create_trigger_commit
    echo ""
    
    trigger_github_actions
    echo ""
    
    check_docker_registry
    echo ""
    
    check_argocd_status
    echo ""
    
    health_check
    echo ""
    
    performance_benchmark
    echo ""
    
    generate_deployment_report
    
    echo ""
    echo "🎉 GitOps 동기화 프로세스 완료!"
    echo ""
    echo "📊 모니터링 링크:"
    echo "- GitHub Actions: https://github.com/$GITHUB_REPO/actions"
    echo "- ArgoCD: $ARGOCD_URL/applications/$HELM_CHART_NAME"
    echo "- 애플리케이션: http://localhost:32542/health"
    echo ""
    echo "⏱️  예상 배포 시간: 5-10분"
    echo "✅ CI/CD 파이프라인이 자동으로 실행됩니다."
}

# 스크립트가 직접 실행될 때만 main 함수 호출
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi