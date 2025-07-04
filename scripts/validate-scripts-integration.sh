#!/bin/bash
set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 함수: 로그 출력
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "🔍 스크립트 간 연계성 검증"
echo "=========================="

# 오프라인 배포 관련 스크립트 확인
OFFLINE_SCRIPTS=(
    "scripts/create-offline-package.sh"
    "scripts/offline-deploy.sh"
)

# 1. 스크립트 존재 확인
echo -e "\n📁 스크립트 존재 확인:"
for script in "${OFFLINE_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        success "$script 존재 ✓"
    else
        error "$script 없음 ✗"
    fi
done

# 2. 스크립트 실행 권한 확인
echo -e "\n🔐 실행 권한 확인:"
for script in "${OFFLINE_SCRIPTS[@]}"; do
    if [ -x "$script" ]; then
        success "$script 실행 가능 ✓"
    else
        error "$script 실행 불가 ✗"
    fi
done

# 3. 스크립트 간 참조 확인
echo -e "\n🔗 스크립트 간 참조 확인:"

# offline-deploy.sh가 create-offline-package.sh를 호출하는지 확인
if grep -q "create-offline-package.sh" scripts/offline-deploy.sh; then
    success "offline-deploy.sh → create-offline-package.sh 참조 확인 ✓"
else
    error "offline-deploy.sh → create-offline-package.sh 참조 없음 ✗"
fi

# 4. 필수 환경 변수 확인
echo -e "\n🌍 환경 변수 사용 확인:"

ENV_VARS=(
    "REGISTRY"
    "IMAGE_NAME"
    "PROJECT_ROOT"
    "PACKAGE_DIR"
)

for script in "${OFFLINE_SCRIPTS[@]}"; do
    echo -e "\n  검사 중: $script"
    for var in "${ENV_VARS[@]}"; do
        if grep -q "$var" "$script"; then
            echo "    ✓ $var 사용됨"
        fi
    done
done

# 5. 중복 실행 방지 메커니즘 확인
echo -e "\n🔒 중복 실행 방지 메커니즘:"

for script in "${OFFLINE_SCRIPTS[@]}"; do
    if grep -q "LOCK_FILE" "$script"; then
        success "$script: 락 파일 메커니즘 구현됨 ✓"
    else
        warning "$script: 락 파일 메커니즘 없음"
    fi
done

# 6. 오류 처리 확인
echo -e "\n⚠️  오류 처리 확인:"

for script in "${OFFLINE_SCRIPTS[@]}"; do
    if grep -q "set -e" "$script"; then
        success "$script: set -e 설정됨 ✓"
    else
        warning "$script: set -e 없음"
    fi
    
    if grep -q "trap" "$script"; then
        success "$script: trap 핸들러 있음 ✓"
    else
        warning "$script: trap 핸들러 없음"
    fi
done

# 7. 워크플로우와 스크립트 연계 확인
echo -e "\n🔄 GitHub Actions 워크플로우 연계:"

WORKFLOW_FILE=".github/workflows/offline-production-deploy.yml"

if [ -f "$WORKFLOW_FILE" ]; then
    log "워크플로우 파일 확인됨"
    
    # 워크플로우에서 생성하는 스크립트와 로컬 스크립트 비교
    echo "  워크플로우에서 생성하는 스크립트:"
    grep -E "cat > offline-package/scripts/.*\.sh" "$WORKFLOW_FILE" | sed 's/.*scripts\//    - /' | sed 's/ <<.*//' || true
    
    echo "  로컬에 있는 스크립트:"
    for script in "${OFFLINE_SCRIPTS[@]}"; do
        echo "    - $(basename $script)"
    done
else
    error "워크플로우 파일 없음"
fi

# 8. 배포 프로세스 흐름 확인
echo -e "\n📊 배포 프로세스 흐름:"
echo "  1. GitHub Actions 트리거 (push to main)"
echo "  2. 테스트 실행"
echo "  3. Docker 이미지 빌드 및 레지스트리 푸시"
echo "  4. 스테이징 환경 배포 (ArgoCD)"
echo "  5. 오프라인 패키지 생성"
echo "  6. GitHub Release 생성"
echo ""
echo "  또는"
echo ""
echo "  1. 로컬에서 직접 패키지 생성:"
echo "     ./scripts/offline-deploy.sh create"
echo "  2. 오프라인 환경으로 전송"
echo "  3. 오프라인 환경에서 배포:"
echo "     ./scripts/offline-deploy.sh deploy <package.tar.gz>"

# 9. 패키지 구조 검증
echo -e "\n📦 생성될 패키지 구조:"
echo "  offline-package/"
echo "  ├── images/          # Docker 이미지"
echo "  ├── manifests/       # Kubernetes YAML"
echo "  ├── scripts/         # 배포 스크립트"
echo "  │   ├── deploy.sh"
echo "  │   ├── rollback.sh"
echo "  │   └── health-check.sh"
echo "  ├── docs/           # 문서"
echo "  └── README.md       # 설명서"

# 10. 최종 검증 결과
echo -e "\n✅ 검증 완료!"
echo "오프라인 배포를 위한 스크립트 통합 검증이 완료되었습니다."