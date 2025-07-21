#!/bin/bash
# CI/CD 안정화 시스템 검증 스크립트

set -e

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 검증 결과 추적
PASSED=0
FAILED=0
WARNINGS=0

echo -e "${BLUE}=== CI/CD 안정화 시스템 검증 ===${NC}"
echo -e "프로젝트 루트: $PROJECT_ROOT"
echo ""

# 1. 필수 파일 확인
echo -e "${YELLOW}1. 필수 파일 확인${NC}"
FILES=(
    ".github/workflows/stable-production-cicd.yml"
    "scripts/deployment-buffer.sh"
    "scripts/cicd-monitor.sh"
    "scripts/blacklist-deployment-worker.service"
    "k8s-gitops/README.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ✅ $file"
        ((PASSED++))
    else
        echo -e "  ❌ $file - 파일 없음"
        ((FAILED++))
    fi
done

# 2. 스크립트 실행 권한 확인
echo -e "\n${YELLOW}2. 스크립트 실행 권한${NC}"
SCRIPTS=(
    "scripts/deployment-buffer.sh"
    "scripts/cicd-monitor.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -x "$script" ]; then
        echo -e "  ✅ $script - 실행 가능"
        ((PASSED++))
    else
        echo -e "  ⚠️  $script - 실행 권한 없음"
        chmod +x "$script"
        echo -e "     → 실행 권한 추가됨"
        ((WARNINGS++))
    fi
done

# 3. CI/CD 워크플로우 검증
echo -e "\n${YELLOW}3. CI/CD 워크플로우 검증${NC}"

# 재시도 로직 확인
if grep -q "MAX_RETRIES" .github/workflows/stable-production-cicd.yml 2>/dev/null; then
    RETRY_COUNT=$(grep -c "attempt.*MAX_RETRIES" .github/workflows/stable-production-cicd.yml)
    echo -e "  ✅ 재시도 로직 설정됨 ($RETRY_COUNT곳)"
    ((PASSED++))
else
    echo -e "  ❌ 재시도 로직 없음"
    ((FAILED++))
fi

# 동시성 제어 확인
if grep -q "concurrency:" .github/workflows/stable-production-cicd.yml 2>/dev/null; then
    echo -e "  ✅ 동시성 제어 설정됨"
    ((PASSED++))
else
    echo -e "  ❌ 동시성 제어 없음"
    ((FAILED++))
fi

# 롤백 메커니즘 확인
if grep -q "rollout undo" .github/workflows/stable-production-cicd.yml 2>/dev/null; then
    echo -e "  ✅ 롤백 메커니즘 있음"
    ((PASSED++))
else
    echo -e "  ❌ 롤백 메커니즘 없음"
    ((FAILED++))
fi

# 헬스체크 확인
if grep -q "health" .github/workflows/stable-production-cicd.yml 2>/dev/null; then
    HEALTH_COUNT=$(grep -c "health" .github/workflows/stable-production-cicd.yml)
    echo -e "  ✅ 헬스체크 설정됨 ($HEALTH_COUNT곳)"
    ((PASSED++))
else
    echo -e "  ❌ 헬스체크 없음"
    ((FAILED++))
fi

# 4. 배포 버퍼링 시스템 테스트
echo -e "\n${YELLOW}4. 배포 버퍼링 시스템 테스트${NC}"

# 큐 초기 상태 확인
./scripts/deployment-buffer.sh clear >/dev/null 2>&1
if ./scripts/deployment-buffer.sh status 2>/dev/null | grep -q '큐가 비어있습니다'; then
    echo -e "  ✅ 큐 초기화 성공"
    ((PASSED++))
else
    echo -e "  ❌ 큐 초기화 실패"
    ((FAILED++))
fi

# 배포 추가 테스트
./scripts/deployment-buffer.sh enqueue test-v1 dev normal >/dev/null 2>&1
./scripts/deployment-buffer.sh enqueue test-v2 prod high >/dev/null 2>&1

QUEUE_COUNT=$(./scripts/deployment-buffer.sh status 2>/dev/null | grep "총" | awk '{print $2}')
if [ "$QUEUE_COUNT" == "2개의" ]; then
    echo -e "  ✅ 배포 큐 추가 성공"
    ((PASSED++))
else
    echo -e "  ❌ 배포 큐 추가 실패 (큐 개수: $QUEUE_COUNT)"
    ((FAILED++))
fi

# 우선순위 확인  
QUEUE_OUTPUT=$(./scripts/deployment-buffer.sh status 2>/dev/null)
echo -e "\n  큐 상태:"
echo "$QUEUE_OUTPUT" | grep -E "test-v[12]" | while read line; do
    echo "    $line"
done

# 큐 정리
./scripts/deployment-buffer.sh clear >/dev/null 2>&1

# 5. 모니터링 시스템 테스트
echo -e "\n${YELLOW}5. 모니터링 시스템 테스트${NC}"

# 메트릭 파일 생성 확인
./scripts/cicd-monitor.sh collect "test-pipeline" "build" "success" "120" >/dev/null 2>&1
if [ -f "/tmp/blacklist-cicd-metrics.json" ]; then
    echo -e "  ✅ 메트릭 수집 작동"
    ((PASSED++))
else
    echo -e "  ❌ 메트릭 수집 실패"
    ((FAILED++))
fi

# 리포트 생성 테스트
if ./scripts/cicd-monitor.sh report >/dev/null 2>&1; then
    echo -e "  ✅ 리포트 생성 성공"
    ((PASSED++))
else
    echo -e "  ❌ 리포트 생성 실패"
    ((FAILED++))
fi

# 6. 환경 변수 및 설정 확인
echo -e "\n${YELLOW}6. 환경 설정 확인${NC}"

# Registry 설정 확인
if grep -q "registry.jclee.me" .github/workflows/stable-production-cicd.yml 2>/dev/null; then
    echo -e "  ✅ Registry 설정 올바름 (registry.jclee.me)"
    ((PASSED++))
else
    echo -e "  ❌ Registry 설정 오류"
    ((FAILED++))
fi

# 네임스페이스 확인
if grep -q "namespace.*blacklist" .github/workflows/stable-production-cicd.yml 2>/dev/null; then
    echo -e "  ✅ 네임스페이스 설정 올바름"
    ((PASSED++))
else
    echo -e "  ⚠️  네임스페이스 확인 필요"
    ((WARNINGS++))
fi

# 7. GitOps 구조 확인
echo -e "\n${YELLOW}7. GitOps 구조 확인${NC}"

GITOPS_DIRS=(
    "k8s-gitops/base"
    "k8s-gitops/overlays/dev"
    "k8s-gitops/overlays/staging"
    "k8s-gitops/overlays/prod"
)

for dir in "${GITOPS_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ✅ $dir"
        ((PASSED++))
    else
        echo -e "  ⚠️  $dir - 디렉토리 없음 (GitOps 구조 생성 필요)"
        ((WARNINGS++))
    fi
done

# 8. 주요 기능 검증
echo -e "\n${YELLOW}8. 주요 기능 검증${NC}"

# 병렬 처리 확인
if grep -q "matrix:" .github/workflows/stable-production-cicd.yml 2>/dev/null; then
    echo -e "  ✅ 병렬 처리 설정됨 (matrix strategy)"
    ((PASSED++))
else
    echo -e "  ❌ 병렬 처리 없음"
    ((FAILED++))
fi

# 캐싱 확인
if grep -q "cache" .github/workflows/stable-production-cicd.yml 2>/dev/null; then
    echo -e "  ✅ 캐싱 설정됨"
    ((PASSED++))
else
    echo -e "  ⚠️  캐싱 미설정"
    ((WARNINGS++))
fi

# 스테이징 배포 확인
if grep -q "staging" .github/workflows/stable-production-cicd.yml 2>/dev/null; then
    echo -e "  ✅ 스테이징 환경 배포 포함"
    ((PASSED++))
else
    echo -e "  ❌ 스테이징 환경 없음"
    ((FAILED++))
fi

# 결과 요약
echo -e "\n${BLUE}=== 검증 결과 요약 ===${NC}"
echo -e "✅ 통과: ${GREEN}$PASSED${NC}"
echo -e "❌ 실패: ${RED}$FAILED${NC}"  
echo -e "⚠️  경고: ${YELLOW}$WARNINGS${NC}"

TOTAL=$((PASSED + FAILED + WARNINGS))
if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$((PASSED * 100 / TOTAL))
else
    SUCCESS_RATE=0
fi

echo -e "\n성공률: ${SUCCESS_RATE}%"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✅ CI/CD 안정화 시스템이 정상적으로 구성되었습니다!${NC}"
    
    echo -e "\n${BLUE}다음 단계:${NC}"
    echo -e "1. GitHub에 push하여 CI/CD 파이프라인 테스트"
    echo -e "2. systemd 서비스 설치: sudo cp scripts/blacklist-deployment-worker.service /etc/systemd/system/"
    echo -e "3. 배포 워커 시작: sudo systemctl start blacklist-deployment-worker"
    echo -e "4. 모니터링 시작: ./scripts/cicd-monitor.sh monitor"
    
    exit 0
else
    echo -e "\n${RED}❌ 일부 구성에 문제가 있습니다. 위의 실패 항목을 확인하세요.${NC}"
    exit 1
fi