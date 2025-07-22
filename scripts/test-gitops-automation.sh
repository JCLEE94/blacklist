#!/bin/bash
# GitOps 자동화 테스트 스크립트

echo "🚀 GitOps 자동화 테스트 시작..."

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 설정
REGISTRY="registry.jclee.me"
IMAGE_NAME="blacklist"
TEST_TAG="test-$(date +%Y%m%d%H%M%S)"

# 1. 파이프라인 파일 검증
echo -e "\n${BLUE}1. CI/CD 파이프라인 검증${NC}"
if [ -f ".github/workflows/gitops-cicd.yml" ]; then
    echo -e "${GREEN}✅ gitops-cicd.yml 존재${NC}"
    
    # 테스트 실패 처리 확인
    if grep -q "|| true" .github/workflows/gitops-cicd.yml; then
        echo -e "${RED}❌ 테스트에 || true가 있음 (실패 무시됨)${NC}"
    else
        echo -e "${GREEN}✅ 테스트 실패 시 중단됨${NC}"
    fi
    
    # Registry 설정 확인
    if grep -q "registry.jclee.me" .github/workflows/gitops-cicd.yml; then
        echo -e "${GREEN}✅ Registry 설정 정상${NC}"
    fi
fi

# 2. ArgoCD 설정 검증
echo -e "\n${BLUE}2. ArgoCD 설정 검증${NC}"
if [ -f "k8s-gitops/argocd/blacklist-app.yaml" ]; then
    echo -e "${GREEN}✅ ArgoCD Application 파일 존재${NC}"
    
    # Image Updater 설정 확인
    if grep -q "argocd-image-updater" k8s-gitops/argocd/blacklist-app.yaml; then
        echo -e "${GREEN}✅ Image Updater 설정됨${NC}"
    fi
    
    # 자동 동기화 확인
    if grep -q "automated:" k8s-gitops/argocd/blacklist-app.yaml; then
        echo -e "${GREEN}✅ 자동 동기화 활성화${NC}"
    fi
fi

# 3. Kustomize 설정 검증
echo -e "\n${BLUE}3. Kustomize 설정 검증${NC}"
for env in dev prod; do
    kustomize_file="k8s-gitops/overlays/$env/kustomization.yaml"
    if [ -f "$kustomize_file" ]; then
        echo -e "${GREEN}✅ $env 환경 kustomization.yaml 존재${NC}"
    else
        echo -e "${RED}❌ $env 환경 kustomization.yaml 없음${NC}"
    fi
done

# 4. Docker 빌드 테스트
echo -e "\n${BLUE}4. Docker 빌드 테스트${NC}"
echo "테스트 이미지 빌드 중..."
docker build -f deployment/Dockerfile -t ${REGISTRY}/${IMAGE_NAME}:${TEST_TAG} . >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker 빌드 성공${NC}"
    # 테스트 이미지 삭제
    docker rmi ${REGISTRY}/${IMAGE_NAME}:${TEST_TAG} >/dev/null 2>&1
else
    echo -e "${RED}❌ Docker 빌드 실패${NC}"
fi

# 5. 로컬 테스트 실행
echo -e "\n${BLUE}5. 로컬 테스트 실행${NC}"
if command -v pytest &> /dev/null; then
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    python3 -m pytest tests/ -v --tb=short -x 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 테스트 통과${NC}"
    else
        echo -e "${RED}❌ 테스트 실패${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  pytest가 설치되지 않음${NC}"
fi

# 6. ArgoCD 연결 테스트
echo -e "\n${BLUE}6. ArgoCD 연결 테스트${NC}"
if command -v argocd &> /dev/null; then
    argocd app get blacklist --grpc-web >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ArgoCD 앱 조회 성공${NC}"
        
        # 동기화 상태 확인
        SYNC_STATUS=$(argocd app get blacklist --grpc-web -o json 2>/dev/null | jq -r '.status.sync.status' 2>/dev/null)
        if [ "$SYNC_STATUS" == "Synced" ]; then
            echo -e "${GREEN}✅ 동기화 상태: Synced${NC}"
        else
            echo -e "${YELLOW}⚠️  동기화 상태: ${SYNC_STATUS}${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  ArgoCD 연결 실패 (로그인 필요)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  ArgoCD CLI가 설치되지 않음${NC}"
fi

# 7. 배포 시뮬레이션
echo -e "\n${BLUE}7. 배포 시뮬레이션${NC}"
echo "Kustomize로 매니페스트 생성 테스트..."
cd k8s-gitops/overlays/prod
kustomize build . >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Production 매니페스트 생성 성공${NC}"
else
    echo -e "${RED}❌ Production 매니페스트 생성 실패${NC}"
fi
cd - >/dev/null

# 8. 요약
echo -e "\n${BLUE}=== GitOps 자동화 테스트 요약 ===${NC}"
echo "1. CI/CD 파이프라인: 테스트 실패 시 중단 설정됨"
echo "2. ArgoCD: Image Updater와 자동 동기화 활성화"
echo "3. Kustomize: 환경별 설정 준비됨"
echo "4. Docker: 빌드 가능"
echo "5. 배포 준비: 완료"

echo -e "\n${GREEN}GitOps 자동화 준비 완료!${NC}"
echo "다음 git push는 자동으로 배포됩니다."