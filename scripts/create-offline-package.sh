#!/bin/bash
set -e

# 스크립트 위치와 프로젝트 루트 설정
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PACKAGE_DIR="${PROJECT_ROOT}/offline-package"
TIMESTAMP=$(date +'%Y%m%d-%H%M%S')
VERSION="${1:-v${TIMESTAMP}}"

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

# 함수: 사전 요구사항 확인
check_prerequisites() {
    log "사전 요구사항 확인 중..."
    
    local missing_tools=()
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    # kubectl 확인
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    fi
    
    # jq 확인 (선택사항)
    if ! command -v jq &> /dev/null; then
        warning "jq가 설치되어 있지 않습니다. 일부 기능이 제한될 수 있습니다."
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "다음 도구들이 필요합니다: ${missing_tools[*]}"
        exit 1
    fi
    
    success "모든 사전 요구사항이 충족되었습니다"
}

# 함수: 기존 패키지 정리
cleanup_old_package() {
    if [ -d "$PACKAGE_DIR" ]; then
        log "기존 패키지 디렉토리 정리 중..."
        rm -rf "$PACKAGE_DIR"
    fi
    
    # 이전 빌드 아티팩트 정리
    find "$PROJECT_ROOT" -name "blacklist-offline-*.tar.gz" -mtime +7 -delete 2>/dev/null || true
}

# 함수: 패키지 디렉토리 구조 생성
create_package_structure() {
    log "패키지 디렉토리 구조 생성 중..."
    
    mkdir -p "$PACKAGE_DIR"/{images,manifests,scripts,docs}
    
    success "패키지 디렉토리 구조 생성 완료"
}

# 함수: Docker 이미지 빌드 및 저장
build_and_save_docker_image() {
    log "Docker 이미지 빌드 중..."
    
    cd "$PROJECT_ROOT"
    
    # 이미지 태그 설정
    local REGISTRY="registry.jclee.me"
    local IMAGE_NAME="blacklist"
    local IMAGE_TAG="${VERSION}"
    local FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    
    # Docker 이미지 빌드
    log "Building Docker image: ${FULL_IMAGE}"
    docker build -f deployment/Dockerfile -t "${FULL_IMAGE}" .
    
    if [ $? -ne 0 ]; then
        error "Docker 이미지 빌드 실패"
        exit 1
    fi
    
    # latest 태그도 추가
    docker tag "${FULL_IMAGE}" "${REGISTRY}/${IMAGE_NAME}:latest"
    
    # 이미지를 tar 파일로 저장
    log "Docker 이미지를 파일로 저장 중..."
    docker save "${FULL_IMAGE}" "${REGISTRY}/${IMAGE_NAME}:latest" | gzip > "$PACKAGE_DIR/images/blacklist-${VERSION}.tar.gz"
    
    # Cloudflare 이미지도 저장
    log "Cloudflare 이미지를 파일로 저장 중..."
    docker pull cloudflare/cloudflared:latest
    docker save cloudflare/cloudflared:latest | gzip > "$PACKAGE_DIR/images/cloudflared-latest.tar.gz"
    
    if [ $? -eq 0 ]; then
        success "Docker 이미지 저장 완료: blacklist-${VERSION}.tar.gz"
        ls -lh "$PACKAGE_DIR/images/blacklist-${VERSION}.tar.gz"
    else
        error "Docker 이미지 저장 실패"
        exit 1
    fi
}

# 함수: Kubernetes 매니페스트 준비
prepare_kubernetes_manifests() {
    log "Kubernetes 매니페스트 준비 중..."
    
    # k8s 디렉토리의 모든 YAML 파일 복사
    cp -r "$PROJECT_ROOT/k8s/"*.yaml "$PACKAGE_DIR/manifests/" 2>/dev/null || true
    
    # 오프라인 프로덕션용 kustomization 생성
    cat > "$PACKAGE_DIR/manifests/kustomization-offline.yaml" << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml
  - secrets.yaml
  - ingress.yaml
  - cloudflared-deployment.yaml

namespace: blacklist-prod

images:
  - name: registry.jclee.me/blacklist
    newTag: ${VERSION}

replicas:
  - name: blacklist
    count: 3

configMapGenerator:
  - name: blacklist-config
    behavior: merge
    literals:
      - ENVIRONMENT=production
      - PORT=2541
      - LOG_LEVEL=info

commonLabels:
  app: blacklist
  version: ${VERSION}
  environment: production
EOF
    
    # 프로덕션용 secrets 템플릿 생성
    cat > "$PACKAGE_DIR/manifests/secrets-template.yaml" << 'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: blacklist-secrets
  namespace: blacklist-prod
type: Opaque
stringData:
  REGTECH_USERNAME: "your-regtech-username"
  REGTECH_PASSWORD: "your-regtech-password"
  SECUDIUM_USERNAME: "your-secudium-username"
  SECUDIUM_PASSWORD: "your-secudium-password"
  SECRET_KEY: "your-flask-secret-key"
  JWT_SECRET_KEY: "your-jwt-secret-key"
EOF
    
    success "Kubernetes 매니페스트 준비 완료"
}

# 함수: 배포 스크립트 생성
create_deployment_scripts() {
    log "배포 스크립트 생성 중..."
    
    # 메인 배포 스크립트
    cat > "$PACKAGE_DIR/scripts/deploy.sh" << 'DEPLOY_SCRIPT'
#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 중복 실행 방지
LOCK_FILE="/tmp/blacklist-deployment.lock"
if [ -f "$LOCK_FILE" ]; then
    error "배포가 이미 진행 중입니다. ($LOCK_FILE 존재)"
    error "강제로 진행하려면 다음 명령을 실행하세요: rm $LOCK_FILE"
    exit 1
fi

# 클린업 함수
cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

# 락 파일 생성
touch "$LOCK_FILE"

echo "🚀 Blacklist 오프라인 프로덕션 배포"
echo "=================================="
echo "버전: ${VERSION}"
echo "환경: Production (Offline)"
echo ""

# 사전 요구사항 확인
check_prerequisites() {
    log "사전 요구사항 확인 중..."
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        error "Docker가 설치되어 있지 않습니다"
        exit 1
    fi
    
    # kubectl 확인
    if ! command -v kubectl &> /dev/null; then
        error "kubectl이 설치되어 있지 않습니다"
        exit 1
    fi
    
    # Kubernetes 클러스터 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        error "Kubernetes 클러스터에 연결할 수 없습니다"
        exit 1
    fi
    
    success "모든 사전 요구사항이 충족되었습니다"
}

# Docker 이미지 로드
load_docker_images() {
    log "Docker 이미지 로드 중..."
    
    for image in "$PACKAGE_DIR"/images/*.tar.gz; do
        if [ -f "$image" ]; then
            log "로드 중: $(basename "$image")"
            gunzip -c "$image" | docker load
            if [ $? -eq 0 ]; then
                success "이미지 로드 완료: $(basename "$image")"
            else
                error "이미지 로드 실패: $(basename "$image")"
                exit 1
            fi
        fi
    done
    
    # 로드된 이미지 확인
    docker images | grep blacklist
}

# 네임스페이스 생성
create_namespace() {
    log "네임스페이스 생성 중..."
    
    kubectl create namespace blacklist-prod --dry-run=client -o yaml | kubectl apply -f -
    
    # 네임스페이스에 라벨 추가
    kubectl label namespace blacklist-prod environment=production --overwrite
    
    success "네임스페이스 준비 완료"
}

# Secrets 확인 및 생성
setup_secrets() {
    log "Secrets 설정 중..."
    
    # secrets-template.yaml이 수정되었는지 확인
    if grep -q "your-" "$PACKAGE_DIR/manifests/secrets-template.yaml"; then
        warning "secrets-template.yaml 파일이 아직 수정되지 않았습니다"
        warning "실제 인증 정보로 업데이트한 후 다음 명령을 실행하세요:"
        echo "kubectl apply -f $PACKAGE_DIR/manifests/secrets-template.yaml"
        echo ""
        read -p "계속 진행하시겠습니까? (secrets는 나중에 수동으로 적용) [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "배포가 취소되었습니다"
            exit 1
        fi
    else
        kubectl apply -f "$PACKAGE_DIR/manifests/secrets-template.yaml"
        success "Secrets 적용 완료"
    fi
}

# Kubernetes 리소스 배포
deploy_resources() {
    log "Kubernetes 리소스 배포 중..."
    
    # ConfigMap 먼저 적용
    if [ -f "$PACKAGE_DIR/manifests/configmap.yaml" ]; then
        kubectl apply -f "$PACKAGE_DIR/manifests/configmap.yaml" -n blacklist-prod
    fi
    
    # Kustomize를 사용하여 나머지 리소스 배포
    kubectl apply -k "$PACKAGE_DIR/manifests/" -n blacklist-prod
    
    success "Kubernetes 리소스 배포 완료"
}

# 배포 대기 및 확인
wait_for_deployment() {
    log "배포가 준비될 때까지 대기 중..."
    
    # Deployment rollout 대기
    kubectl rollout status deployment/blacklist -n blacklist-prod --timeout=600s
    
    # Pod 상태 확인
    kubectl get pods -n blacklist-prod -l app=blacklist
    
    success "배포가 성공적으로 완료되었습니다"
}

# 헬스체크 실행
run_health_check() {
    log "애플리케이션 헬스체크 실행 중..."
    
    # 첫 번째 실행 중인 Pod 찾기
    POD_NAME=$(kubectl get pods -n blacklist-prod -l app=blacklist -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
    
    if [ -z "$POD_NAME" ]; then
        error "실행 중인 Pod을 찾을 수 없습니다"
        return 1
    fi
    
    log "Pod에서 헬스체크 실행: $POD_NAME"
    
    # 헬스체크 엔드포인트 호출
    HEALTH_RESPONSE=$(kubectl exec -n blacklist-prod "$POD_NAME" -- curl -s http://localhost:2541/health)
    
    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        success "애플리케이션이 정상적으로 실행 중입니다"
        echo "$HEALTH_RESPONSE" | jq . 2>/dev/null || echo "$HEALTH_RESPONSE"
    else
        error "헬스체크 실패"
        echo "$HEALTH_RESPONSE"
        return 1
    fi
}

# 배포 정보 출력
print_deployment_info() {
    echo ""
    echo "📊 배포 요약"
    echo "=========="
    
    # Deployment 정보
    kubectl get deployment blacklist -n blacklist-prod
    
    echo ""
    # Service 정보
    kubectl get service blacklist -n blacklist-prod
    
    echo ""
    # Ingress 정보 (있는 경우)
    kubectl get ingress -n blacklist-prod 2>/dev/null || true
    
    echo ""
    echo "🎉 배포가 성공적으로 완료되었습니다!"
    echo ""
    echo "애플리케이션 접근 방법:"
    echo "  - 내부: http://blacklist.blacklist-prod.svc.cluster.local:2541"
    echo "  - 외부: Ingress/NodePort 설정에 따라 접근"
    echo ""
    echo "유용한 명령어:"
    echo "  - 로그 확인: kubectl logs -f deployment/blacklist -n blacklist-prod"
    echo "  - Pod 상태: kubectl get pods -n blacklist-prod"
    echo "  - 스케일링: kubectl scale deployment/blacklist --replicas=5 -n blacklist-prod"
}

# 메인 배포 프로세스
main() {
    check_prerequisites
    load_docker_images
    create_namespace
    setup_secrets
    deploy_resources
    wait_for_deployment
    run_health_check
    print_deployment_info
}

# 메인 함수 실행
main "$@"
DEPLOY_SCRIPT
    
    # 롤백 스크립트
    cat > "$PACKAGE_DIR/scripts/rollback.sh" << 'ROLLBACK_SCRIPT'
#!/bin/bash
set -e

NAMESPACE="blacklist-prod"
DEPLOYMENT="blacklist"

echo "🔄 Blacklist 프로덕션 롤백"
echo "======================="

# 현재 리비전 확인
CURRENT_REVISION=$(kubectl rollout history deployment/$DEPLOYMENT -n $NAMESPACE --output=jsonpath='{.metadata.generation}')
echo "현재 리비전: $CURRENT_REVISION"

# 롤백 가능한 리비전 목록
echo ""
echo "롤백 가능한 리비전:"
kubectl rollout history deployment/$DEPLOYMENT -n $NAMESPACE

# 롤백 실행
read -p "롤백할 리비전 번호를 입력하세요 (0 = 이전 버전): " REVISION

if [ "$REVISION" == "0" ]; then
    echo "이전 버전으로 롤백 중..."
    kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE
else
    echo "리비전 $REVISION(으)로 롤백 중..."
    kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE --to-revision=$REVISION
fi

# 롤백 상태 확인
kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE --timeout=300s

echo "✅ 롤백이 완료되었습니다"
kubectl get pods -n $NAMESPACE -l app=blacklist
ROLLBACK_SCRIPT
    
    # 헬스체크 스크립트
    cat > "$PACKAGE_DIR/scripts/health-check.sh" << 'HEALTH_SCRIPT'
#!/bin/bash

NAMESPACE="blacklist-prod"

echo "🏥 Blacklist 프로덕션 헬스체크"
echo "============================"

# Deployment 상태
echo "📊 Deployment 상태:"
kubectl get deployment blacklist -n $NAMESPACE -o wide

echo ""
# Pod 상태
echo "📦 Pod 상태:"
kubectl get pods -n $NAMESPACE -l app=blacklist -o wide

echo ""
# Service 상태
echo "🌐 Service 상태:"
kubectl get service blacklist -n $NAMESPACE

echo ""
# 리소스 사용량
echo "💾 리소스 사용량:"
kubectl top pods -n $NAMESPACE -l app=blacklist 2>/dev/null || echo "Metrics server가 설치되어 있지 않습니다"

echo ""
# 애플리케이션 헬스체크
echo "💊 애플리케이션 헬스체크:"
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=blacklist -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)

if [ -n "$POD_NAME" ]; then
    echo "Pod: $POD_NAME"
    kubectl exec -n $NAMESPACE "$POD_NAME" -- curl -s http://localhost:2541/health | jq . 2>/dev/null || echo "헬스체크 실패"
else
    echo "실행 중인 Pod을 찾을 수 없습니다"
fi

echo ""
# 최근 이벤트
echo "📅 최근 이벤트:"
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10
HEALTH_SCRIPT
    
    # 모든 스크립트에 실행 권한 부여
    chmod +x "$PACKAGE_DIR/scripts/"*.sh
    
    success "배포 스크립트 생성 완료"
}

# 함수: 문서 생성
create_documentation() {
    log "문서 생성 중..."
    
    # README.md
    cat > "$PACKAGE_DIR/README.md" << EOF
# Blacklist 오프라인 프로덕션 배포 패키지

버전: ${VERSION}
빌드 날짜: $(date +'%Y-%m-%d %H:%M:%S')
빌드 위치: $(hostname)

## 📦 패키지 구성

\`\`\`
offline-package/
├── images/              # Docker 이미지 (압축)
│   └── blacklist-${VERSION}.tar.gz
├── manifests/          # Kubernetes YAML 파일
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secrets-template.yaml
│   ├── ingress.yaml
│   └── kustomization-offline.yaml
├── scripts/            # 배포 스크립트
│   ├── deploy.sh       # 메인 배포 스크립트
│   ├── rollback.sh     # 롤백 스크립트
│   └── health-check.sh # 헬스체크 스크립트
├── docs/              # 추가 문서
└── README.md          # 이 파일
\`\`\`

## 🚀 빠른 시작

### 1. 패키지 전송
이 패키지를 안전한 매체를 통해 오프라인 프로덕션 환경으로 전송합니다.

### 2. 패키지 압축 해제
\`\`\`bash
tar -xzf blacklist-offline-${VERSION}.tar.gz
cd blacklist-offline-${VERSION}
\`\`\`

### 3. Secrets 설정
\`manifests/secrets-template.yaml\` 파일을 편집하여 실제 인증 정보를 입력합니다.

### 4. 배포 실행
\`\`\`bash
./scripts/deploy.sh
\`\`\`

## 📋 사전 요구사항

- **Kubernetes 클러스터**: 프로덕션 클러스터 접근 가능
- **Docker**: 이미지 로드를 위해 필요
- **kubectl**: 클러스터 접근 설정 완료
- **네임스페이스**: \`blacklist-prod\` (자동 생성됨)

## 🔧 상세 배포 가이드

### Secrets 설정
1. \`manifests/secrets-template.yaml\` 파일 편집
2. 다음 값들을 실제 값으로 변경:
   - REGTECH_USERNAME
   - REGTECH_PASSWORD
   - SECUDIUM_USERNAME
   - SECUDIUM_PASSWORD
   - SECRET_KEY
   - JWT_SECRET_KEY

### 배포 프로세스
1. Docker 이미지 로드
2. Kubernetes 네임스페이스 생성
3. Secrets 및 ConfigMap 적용
4. Deployment, Service, Ingress 배포
5. 헬스체크 실행

### 배포 확인
\`\`\`bash
./scripts/health-check.sh
\`\`\`

## 🔄 운영 가이드

### 스케일링
\`\`\`bash
kubectl scale deployment/blacklist --replicas=5 -n blacklist-prod
\`\`\`

### 로그 확인
\`\`\`bash
kubectl logs -f deployment/blacklist -n blacklist-prod
\`\`\`

### 롤백
\`\`\`bash
./scripts/rollback.sh
\`\`\`

## ⚠️ 주의사항

1. **중복 실행 방지**: 배포 스크립트는 동시 실행을 방지합니다
2. **Secrets 보안**: secrets 파일은 안전하게 관리하세요
3. **백업**: ..배포 전 현재 상태를 백업하세요

## 🐛 문제 해결

### Docker 이미지 로드 실패
- 디스크 공간 확인
- Docker 데몬 상태 확인
- 이미지 파일 무결성 확인

### Pod 시작 실패
- \`kubectl describe pod -n blacklist-prod\`로 상세 정보 확인
- 이미지 pull 정책 확인
- 리소스 제한 확인

### 헬스체크 실패
- Pod 로그 확인
- 네트워크 정책 확인
- 환경 변수 설정 확인

## 📞 지원

문제 발생 시:
1. 로그 확인: \`kubectl logs -f deployment/blacklist -n blacklist-prod\`
2. 이벤트 확인: \`kubectl get events -n blacklist-prod\`
3. 헬스체크: \`./scripts/health-check.sh\`

---
Generated on: $(date)
EOF
    
    # 체크리스트 문서
    cat > "$PACKAGE_DIR/docs/deployment-checklist.md" << 'EOF'
# 배포 체크리스트

## 배포 전 확인사항
- [ ] Kubernetes 클러스터 접근 가능
- [ ] Docker 설치 및 실행 중
- [ ] kubectl 설정 완료
- [ ] 필요한 네임스페이스 권한 보유
- [ ] Secrets 정보 준비

## 배포 단계
- [ ] 패키지 무결성 확인
- [ ] Secrets 파일 수정
- [ ] 배포 스크립트 실행
- [ ] Pod 상태 확인
- [ ] 헬스체크 통과
- [ ] 서비스 접근 테스트

## 배포 후 확인사항
- [ ] 모든 Pod Running 상태
- [ ] 서비스 엔드포인트 활성
- [ ] 로그에 에러 없음
- [ ] 외부 접근 가능 (Ingress/NodePort)
- [ ] 모니터링 설정

## 롤백 준비
- [ ] 이전 버전 정보 기록
- [ ] 롤백 절차 숙지
- [ ] 롤백 스크립트 테스트
EOF
    
    success "문서 생성 완료"
}

# 함수: 패키지 최종 생성
create_final_package() {
    log "최종 패키지 생성 중..."
    
    cd "$PROJECT_ROOT"
    
    # 패키지 압축
    PACKAGE_NAME="blacklist-offline-${VERSION}.tar.gz"
    tar -czf "$PACKAGE_NAME" -C offline-package .
    
    # 체크섬 생성
    sha256sum "$PACKAGE_NAME" > "${PACKAGE_NAME}.sha256"
    
    # 패키지 크기 확인
    PACKAGE_SIZE=$(ls -lh "$PACKAGE_NAME" | awk '{print $5}')
    
    success "오프라인 배포 패키지 생성 완료"
    echo ""
    echo "📦 패키지 정보:"
    echo "  - 파일명: $PACKAGE_NAME"
    echo "  - 크기: $PACKAGE_SIZE"
    echo "  - 위치: $PROJECT_ROOT/$PACKAGE_NAME"
    echo "  - 체크섬: $(cat "${PACKAGE_NAME}.sha256")"
}

# 메인 실행 흐름
main() {
    echo "🚀 Blacklist 오프라인 배포 패키지 생성"
    echo "===================================="
    echo "버전: ${VERSION}"
    echo ""
    
    check_prerequisites
    cleanup_old_package
    create_package_structure
    build_and_save_docker_image
    prepare_kubernetes_manifests
    create_deployment_scripts
    create_documentation
    create_final_package
    
    echo ""
    echo "✅ 오프라인 배포 패키지 생성이 완료되었습니다!"
    echo ""
    echo "다음 단계:"
    echo "1. 패키지를 안전한 매체로 프로덕션 환경에 전송"
    echo "2. 패키지 압축 해제 후 ./scripts/deploy.sh 실행"
    echo "3. README.md의 지침을 따라 배포 진행"
}

# 스크립트 실행
main "$@"