#!/bin/bash
set -e

# 스크립트 위치와 프로젝트 루트 설정
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수: 로그 출력
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 함수: 사용법 출력
usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  create    - 오프라인 배포 패키지 생성"
    echo "  deploy    - 오프라인 패키지를 사용하여 배포"
    echo "  status    - 현재 배포 상태 확인"
    echo "  rollback  - 이전 버전으로 롤백"
    echo ""
    echo "예제:"
    echo "  $0 create               # 패키지 생성"
    echo "  $0 deploy package.tar.gz  # 패키지 배포"
    echo "  $0 status               # 상태 확인"
    echo "  $0 rollback             # 롤백"
}

# 함수: 패키지 생성
create_package() {
    log "오프라인 배포 패키지 생성을 시작합니다..."
    
    # create-offline-package.sh 스크립트 실행
    if [ -f "$SCRIPT_DIR/create-offline-package.sh" ]; then
        "$SCRIPT_DIR/create-offline-package.sh" "$@"
    else
        error "create-offline-package.sh 스크립트를 찾을 수 없습니다"
        exit 1
    fi
}

# 함수: 패키지 배포
deploy_package() {
    local PACKAGE_FILE="$1"
    
    if [ -z "$PACKAGE_FILE" ]; then
        error "패키지 파일을 지정해주세요"
        echo "사용법: $0 deploy <package-file.tar.gz>"
        exit 1
    fi
    
    if [ ! -f "$PACKAGE_FILE" ]; then
        error "패키지 파일을 찾을 수 없습니다: $PACKAGE_FILE"
        exit 1
    fi
    
    log "패키지 배포를 시작합니다: $PACKAGE_FILE"
    
    # 임시 디렉토리 생성
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_DIR" EXIT
    
    # 패키지 압축 해제
    log "패키지 압축 해제 중..."
    tar -xzf "$PACKAGE_FILE" -C "$TEMP_DIR"
    
    # 배포 스크립트 실행
    if [ -f "$TEMP_DIR/scripts/deploy.sh" ]; then
        log "배포 스크립트 실행 중..."
        cd "$TEMP_DIR"
        ./scripts/deploy.sh
    else
        error "배포 스크립트를 찾을 수 없습니다"
        exit 1
    fi
}

# 함수: 상태 확인
check_status() {
    log "배포 상태 확인 중..."
    
    local NAMESPACE="blacklist-prod"
    
    # Kubernetes 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        error "Kubernetes 클러스터에 연결할 수 없습니다"
        exit 1
    fi
    
    echo ""
    echo "📊 Deployment 상태:"
    kubectl get deployment blacklist -n $NAMESPACE 2>/dev/null || echo "Deployment를 찾을 수 없습니다"
    
    echo ""
    echo "📦 Pod 상태:"
    kubectl get pods -n $NAMESPACE -l app=blacklist 2>/dev/null || echo "Pod를 찾을 수 없습니다"
    
    echo ""
    echo "🌐 Service 상태:"
    kubectl get service blacklist -n $NAMESPACE 2>/dev/null || echo "Service를 찾을 수 없습니다"
    
    echo ""
    echo "💊 헬스체크:"
    POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=blacklist -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
    if [ -n "$POD_NAME" ]; then
        kubectl exec -n $NAMESPACE "$POD_NAME" -- curl -s http://localhost:2541/health 2>/dev/null | jq . 2>/dev/null || echo "헬스체크 실패"
    else
        echo "실행 중인 Pod를 찾을 수 없습니다"
    fi
}

# 함수: 롤백
rollback_deployment() {
    log "롤백을 시작합니다..."
    
    local NAMESPACE="blacklist-prod"
    local DEPLOYMENT="blacklist"
    
    # Kubernetes 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        error "Kubernetes 클러스터에 연결할 수 없습니다"
        exit 1
    fi
    
    # 현재 리비전 확인
    echo "현재 배포 히스토리:"
    kubectl rollout history deployment/$DEPLOYMENT -n $NAMESPACE
    
    echo ""
    read -p "롤백을 진행하시겠습니까? [y/N] " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "이전 버전으로 롤백 중..."
        kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE
        
        # 롤백 상태 확인
        kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE --timeout=300s
        
        success "롤백이 완료되었습니다"
        
        # 새로운 상태 확인
        check_status
    else
        warning "롤백이 취소되었습니다"
    fi
}

# 함수: 빠른 배포 (로컬 빌드 + 배포)
quick_deploy() {
    log "빠른 배포 모드 (로컬 빌드 + 즉시 배포)"
    
    # 버전 생성
    VERSION="v$(date +'%Y%m%d-%H%M%S')"
    
    # 패키지 생성
    log "패키지 생성 중..."
    create_package "$VERSION"
    
    # 생성된 패키지 찾기
    PACKAGE_FILE="$PROJECT_ROOT/blacklist-offline-${VERSION}.tar.gz"
    
    if [ ! -f "$PACKAGE_FILE" ]; then
        error "패키지 파일을 찾을 수 없습니다"
        exit 1
    fi
    
    # 즉시 배포
    log "패키지 배포 중..."
    deploy_package "$PACKAGE_FILE"
}

# 메인 로직
main() {
    case "$1" in
        create)
            shift
            create_package "$@"
            ;;
        deploy)
            shift
            deploy_package "$@"
            ;;
        status)
            check_status
            ;;
        rollback)
            rollback_deployment
            ;;
        quick)
            quick_deploy
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

# 중복 실행 방지
LOCK_FILE="/tmp/blacklist-offline-deploy.lock"

# 클린업 함수
cleanup() {
    rm -f "$LOCK_FILE"
}

# create와 status 명령은 락 체크 없이 실행
if [[ "$1" != "create" && "$1" != "status" ]]; then
    if [ -f "$LOCK_FILE" ]; then
        error "다른 배포 작업이 진행 중입니다. ($LOCK_FILE 존재)"
        error "강제로 진행하려면 다음 명령을 실행하세요: rm $LOCK_FILE"
        exit 1
    fi
    
    # 트랩 설정 및 락 파일 생성
    trap cleanup EXIT
    touch "$LOCK_FILE"
fi

# 메인 함수 실행
main "$@"