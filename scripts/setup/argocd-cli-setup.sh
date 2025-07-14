#!/bin/bash

# ArgoCD CLI 기반 설정 스크립트
# 이 스크립트는 ArgoCD CLI를 사용하여 전체 설정을 수행합니다.

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 기본 설정
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"
ARGOCD_NAMESPACE="argocd"
APP_NAME="blacklist"
APP_NAMESPACE="blacklist"
GITHUB_REPO="https://github.com/JCLEE94/blacklist.git"
GITHUB_BRANCH="main"
K8S_PATH="k8s"
REGISTRY="registry.jclee.me"
IMAGE_NAME="jclee94/blacklist"

echo -e "${BLUE}=== ArgoCD CLI 설정 시작 ===${NC}"

# 1. ArgoCD CLI 설치 확인 및 설치
check_argocd_cli() {
    echo -e "${YELLOW}ArgoCD CLI 확인 중...${NC}"
    
    if command -v argocd &> /dev/null; then
        echo -e "${GREEN}✓ ArgoCD CLI가 이미 설치되어 있습니다.${NC}"
        argocd version --client
    else
        echo -e "${YELLOW}ArgoCD CLI를 설치합니다...${NC}"
        
        # 최신 버전 다운로드
        curl -sSL -o /tmp/argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
        
        # 실행 권한 설정 및 설치
        sudo install -m 555 /tmp/argocd-linux-amd64 /usr/local/bin/argocd
        rm /tmp/argocd-linux-amd64
        
        echo -e "${GREEN}✓ ArgoCD CLI 설치 완료${NC}"
        argocd version --client
    fi
}

# 2. kubectl 설정 확인
check_kubectl() {
    echo -e "${YELLOW}kubectl 설정 확인 중...${NC}"
    
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}✗ kubectl이 설치되지 않았습니다.${NC}"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}✗ Kubernetes 클러스터에 연결할 수 없습니다.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ kubectl 설정 확인 완료${NC}"
}

# 3. ArgoCD 설치 확인
check_argocd_installation() {
    echo -e "${YELLOW}ArgoCD 설치 확인 중...${NC}"
    
    if kubectl get namespace $ARGOCD_NAMESPACE &> /dev/null; then
        echo -e "${GREEN}✓ ArgoCD 네임스페이스가 존재합니다.${NC}"
        
        # ArgoCD 서버 상태 확인
        if kubectl get deployment argocd-server -n $ARGOCD_NAMESPACE &> /dev/null; then
            echo -e "${GREEN}✓ ArgoCD 서버가 실행 중입니다.${NC}"
        else
            echo -e "${RED}✗ ArgoCD 서버가 실행되지 않습니다.${NC}"
            echo -e "${YELLOW}ArgoCD를 설치하시겠습니까? (y/n)${NC}"
            read -r install_argocd
            if [[ "$install_argocd" == "y" ]]; then
                install_argocd_server
            else
                exit 1
            fi
        fi
    else
        echo -e "${YELLOW}ArgoCD가 설치되지 않았습니다. 설치하시겠습니까? (y/n)${NC}"
        read -r install_argocd
        if [[ "$install_argocd" == "y" ]]; then
            install_argocd_server
        else
            exit 1
        fi
    fi
}

# 4. ArgoCD 서버 설치
install_argocd_server() {
    echo -e "${YELLOW}ArgoCD 서버를 설치합니다...${NC}"
    
    # 네임스페이스 생성
    kubectl create namespace $ARGOCD_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # ArgoCD 설치
    kubectl apply -n $ARGOCD_NAMESPACE -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    
    echo -e "${YELLOW}ArgoCD 서버가 준비될 때까지 대기 중...${NC}"
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n $ARGOCD_NAMESPACE
    
    echo -e "${GREEN}✓ ArgoCD 서버 설치 완료${NC}"
}

# 5. ArgoCD 서버 로그인
login_argocd() {
    echo -e "${YELLOW}ArgoCD 서버에 로그인 중...${NC}"
    
    # 초기 admin 비밀번호 가져오기
    if [ -z "$ARGOCD_PASSWORD" ]; then
        echo -e "${YELLOW}ArgoCD admin 비밀번호를 가져옵니다...${NC}"
        ARGOCD_PASSWORD=$(kubectl -n $ARGOCD_NAMESPACE get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
        echo -e "${GREEN}초기 admin 비밀번호: ${ARGOCD_PASSWORD}${NC}"
        echo -e "${YELLOW}이 비밀번호를 안전한 곳에 저장하세요!${NC}"
    fi
    
    # 로그인
    argocd login $ARGOCD_SERVER --username admin --password "$ARGOCD_PASSWORD" --grpc-web --insecure
    
    echo -e "${GREEN}✓ ArgoCD 로그인 성공${NC}"
}

# 6. GitHub Repository 추가
add_repository() {
    echo -e "${YELLOW}GitHub Repository 추가 중...${NC}"
    
    # Public repository인 경우
    if argocd repo list | grep -q "$GITHUB_REPO"; then
        echo -e "${GREEN}✓ Repository가 이미 등록되어 있습니다.${NC}"
    else
        argocd repo add $GITHUB_REPO --grpc-web
        echo -e "${GREEN}✓ Repository 추가 완료${NC}"
    fi
}

# 7. ArgoCD Application 생성
create_application() {
    echo -e "${YELLOW}ArgoCD Application 생성 중...${NC}"
    
    # 기존 애플리케이션 확인
    if argocd app get $APP_NAME &> /dev/null; then
        echo -e "${YELLOW}기존 애플리케이션이 존재합니다. 삭제하고 다시 생성하시겠습니까? (y/n)${NC}"
        read -r delete_app
        if [[ "$delete_app" == "y" ]]; then
            argocd app delete $APP_NAME --cascade --grpc-web
            sleep 5
        else
            echo -e "${YELLOW}기존 애플리케이션을 유지합니다.${NC}"
            return
        fi
    fi
    
    # 애플리케이션 생성
    argocd app create $APP_NAME \
        --repo $GITHUB_REPO \
        --path $K8S_PATH \
        --dest-server https://kubernetes.default.svc \
        --dest-namespace $APP_NAMESPACE \
        --revision $GITHUB_BRANCH \
        --sync-policy automated \
        --sync-option CreateNamespace=true \
        --sync-option PrunePropagationPolicy=foreground \
        --sync-option PruneLast=true \
        --self-heal \
        --auto-prune \
        --grpc-web
    
    echo -e "${GREEN}✓ Application 생성 완료${NC}"
}

# 8. ArgoCD Image Updater 설정
configure_image_updater() {
    echo -e "${YELLOW}ArgoCD Image Updater 설정 중...${NC}"
    
    # Image Updater 설치 확인
    if ! kubectl get deployment argocd-image-updater -n $ARGOCD_NAMESPACE &> /dev/null; then
        echo -e "${YELLOW}ArgoCD Image Updater를 설치합니다...${NC}"
        kubectl apply -n $ARGOCD_NAMESPACE -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml
        
        kubectl wait --for=condition=available --timeout=300s deployment/argocd-image-updater -n $ARGOCD_NAMESPACE
    fi
    
    # Application에 Image Updater 어노테이션 추가
    echo -e "${YELLOW}Image Updater 어노테이션 추가 중...${NC}"
    argocd app set $APP_NAME \
        --annotations "argocd-image-updater.argoproj.io/image-list=blacklist=$REGISTRY/$IMAGE_NAME:latest" \
        --annotations "argocd-image-updater.argoproj.io/blacklist.update-strategy=latest" \
        --annotations "argocd-image-updater.argoproj.io/write-back-method=git" \
        --annotations "argocd-image-updater.argoproj.io/git-branch=$GITHUB_BRANCH" \
        --annotations "argocd-image-updater.argoproj.io/blacklist.pull-secret=secret:$APP_NAMESPACE/ghcr-secret" \
        --grpc-web
    
    echo -e "${GREEN}✓ Image Updater 설정 완료${NC}"
}

# 9. 초기 동기화
initial_sync() {
    echo -e "${YELLOW}초기 동기화 수행 중...${NC}"
    
    argocd app sync $APP_NAME --grpc-web
    
    # 동기화 상태 확인
    echo -e "${YELLOW}동기화 상태 확인 중...${NC}"
    argocd app wait $APP_NAME --timeout 300 --grpc-web
    
    echo -e "${GREEN}✓ 초기 동기화 완료${NC}"
}

# 10. 설정 요약 출력
print_summary() {
    echo -e "${BLUE}=== ArgoCD 설정 요약 ===${NC}"
    echo -e "ArgoCD 서버: ${GREEN}$ARGOCD_SERVER${NC}"
    echo -e "애플리케이션: ${GREEN}$APP_NAME${NC}"
    echo -e "GitHub Repository: ${GREEN}$GITHUB_REPO${NC}"
    echo -e "Branch: ${GREEN}$GITHUB_BRANCH${NC}"
    echo -e "Kubernetes Path: ${GREEN}$K8S_PATH${NC}"
    echo -e "이미지: ${GREEN}$REGISTRY/$IMAGE_NAME:latest${NC}"
    echo ""
    echo -e "${BLUE}=== 유용한 명령어 ===${NC}"
    echo -e "애플리케이션 상태: ${YELLOW}argocd app get $APP_NAME --grpc-web${NC}"
    echo -e "수동 동기화: ${YELLOW}argocd app sync $APP_NAME --grpc-web${NC}"
    echo -e "로그 확인: ${YELLOW}argocd app logs $APP_NAME --grpc-web${NC}"
    echo -e "웹 UI 접속: ${YELLOW}https://$ARGOCD_SERVER${NC}"
    echo ""
    echo -e "${GREEN}✅ ArgoCD 설정이 완료되었습니다!${NC}"
}

# 메인 실행 흐름
main() {
    echo -e "${BLUE}ArgoCD CLI 기반 설정을 시작합니다...${NC}"
    echo ""
    
    # 단계별 실행
    check_argocd_cli
    check_kubectl
    check_argocd_installation
    login_argocd
    add_repository
    create_application
    configure_image_updater
    initial_sync
    print_summary
}

# 스크립트 실행
main