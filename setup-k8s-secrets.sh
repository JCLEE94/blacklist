#!/bin/bash
# Kubernetes Secret 관리 및 ArgoCD 동기화 스크립트
# jclee.me 인프라에서 blacklist 애플리케이션의 secret 관리

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 환경 변수 확인
check_prerequisites() {
    echo -e "${BLUE}🔍 환경 확인 중...${NC}"
    
    # kubectl 명령어 확인
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl이 설치되어 있지 않습니다${NC}"
        exit 1
    fi
    
    # K8s 클러스터 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}❌ Kubernetes 클러스터에 연결할 수 없습니다${NC}"
        echo "다음 명령어로 연결을 확인하세요:"
        echo "kubectl config use-context k8s-jclee-me"
        exit 1
    fi
    
    # 네임스페이스 확인
    if ! kubectl get namespace default &> /dev/null; then
        echo -e "${RED}❌ default 네임스페이스에 접근할 수 없습니다${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 환경 확인 완료${NC}"
}

# Secret 백업
backup_existing_secret() {
    local secret_name="blacklist-secrets"
    local backup_file="secret-backup-$(date +%Y%m%d-%H%M%S).yaml"
    
    echo -e "${BLUE}📦 기존 Secret 백업 중...${NC}"
    
    if kubectl get secret "$secret_name" -n default &> /dev/null; then
        kubectl get secret "$secret_name" -n default -o yaml > "$backup_file"
        echo -e "${GREEN}✅ 기존 Secret을 $backup_file에 백업했습니다${NC}"
    else
        echo -e "${YELLOW}⚠️  기존 Secret이 존재하지 않습니다${NC}"
    fi
}

# Secret 값 입력 받기
get_secret_values() {
    echo -e "${BLUE}🔐 Secret 값 입력${NC}"
    echo "다음 항목들을 입력하세요 (Enter로 기본값 사용):"
    echo
    
    # REGTECH 자격증명
    read -p "REGTECH_USERNAME [기본값 유지]: " REGTECH_USERNAME
    read -s -p "REGTECH_PASSWORD [기본값 유지]: " REGTECH_PASSWORD
    echo
    
    # SECUDIUM 자격증명
    read -p "SECUDIUM_USERNAME [기본값 유지]: " SECUDIUM_USERNAME
    read -s -p "SECUDIUM_PASSWORD [기본값 유지]: " SECUDIUM_PASSWORD
    echo
    
    # Flask 보안 키
    read -s -p "SECRET_KEY [새로 생성할까요? y/N]: " GENERATE_SECRET
    echo
    if [[ "$GENERATE_SECRET" =~ ^[Yy]$ ]]; then
        SECRET_KEY=$(openssl rand -hex 32)
        echo -e "${GREEN}✅ 새 SECRET_KEY가 생성되었습니다${NC}"
    else
        read -s -p "SECRET_KEY를 입력하세요: " SECRET_KEY
        echo
    fi
    
    read -s -p "JWT_SECRET_KEY [새로 생성할까요? y/N]: " GENERATE_JWT
    echo
    if [[ "$GENERATE_JWT" =~ ^[Yy]$ ]]; then
        JWT_SECRET_KEY=$(openssl rand -hex 32)
        echo -e "${GREEN}✅ 새 JWT_SECRET_KEY가 생성되었습니다${NC}"
    else
        read -s -p "JWT_SECRET_KEY를 입력하세요: " JWT_SECRET_KEY
        echo
    fi
}

# Secret 생성/업데이트
update_secret() {
    local secret_name="blacklist-secrets"
    
    echo -e "${BLUE}🔄 Kubernetes Secret 업데이트 중...${NC}"
    
    # 기존 Secret 삭제
    if kubectl get secret "$secret_name" -n default &> /dev/null; then
        kubectl delete secret "$secret_name" -n default
        echo -e "${YELLOW}🗑️  기존 Secret 삭제 완료${NC}"
    fi
    
    # 새 Secret 생성
    kubectl create secret generic "$secret_name" \
        --namespace=default \
        --from-literal=REGTECH_USERNAME="${REGTECH_USERNAME:-existing-value}" \
        --from-literal=REGTECH_PASSWORD="${REGTECH_PASSWORD:-existing-value}" \
        --from-literal=SECUDIUM_USERNAME="${SECUDIUM_USERNAME:-existing-value}" \
        --from-literal=SECUDIUM_PASSWORD="${SECUDIUM_PASSWORD:-existing-value}" \
        --from-literal=SECRET_KEY="${SECRET_KEY}" \
        --from-literal=JWT_SECRET_KEY="${JWT_SECRET_KEY}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Secret 업데이트 완료${NC}"
    else
        echo -e "${RED}❌ Secret 업데이트 실패${NC}"
        exit 1
    fi
}

# ArgoCD 동기화 트리거
trigger_argocd_sync() {
    echo -e "${BLUE}🔄 ArgoCD 동기화 트리거 중...${NC}"
    
    # ArgoCD CLI가 있는지 확인
    if command -v argocd &> /dev/null; then
        # ArgoCD 서버 로그인 시도
        echo -e "${YELLOW}ArgoCD에 로그인 시도 중...${NC}"
        if argocd login argo.jclee.me --grpc-web --insecure; then
            echo -e "${BLUE}ArgoCD 애플리케이션 동기화 중...${NC}"
            argocd app sync blacklist-production
            argocd app wait blacklist-production --health
            echo -e "${GREEN}✅ ArgoCD 동기화 완료${NC}"
        else
            echo -e "${YELLOW}⚠️  ArgoCD 자동 동기화 실패 - 수동으로 확인하세요${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  ArgoCD CLI가 설치되어 있지 않습니다${NC}"
        echo "ArgoCD UI에서 수동으로 동기화하세요: https://argo.jclee.me"
    fi
}

# 배포 상태 확인
check_deployment_status() {
    echo -e "${BLUE}📊 배포 상태 확인 중...${NC}"
    
    # Pod 상태 확인
    echo -e "${BLUE}Pod 상태:${NC}"
    kubectl get pods -l app=blacklist -n default -o wide
    echo
    
    # Secret 확인
    echo -e "${BLUE}Secret 상태:${NC}"
    kubectl get secret blacklist-secrets -n default
    echo
    
    # Deployment 상태 확인
    echo -e "${BLUE}Deployment 상태:${NC}"
    kubectl get deployment blacklist -n default
    echo
    
    # 롤아웃 상태 대기
    echo -e "${BLUE}롤아웃 완료 대기 중...${NC}"
    kubectl rollout status deployment/blacklist -n default --timeout=300s
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 배포 완료${NC}"
        echo
        echo -e "${BLUE}🌐 접근 URL:${NC}"
        echo "  • 애플리케이션: https://blacklist.jclee.me"
        echo "  • 상태 확인: https://blacklist.jclee.me/health"
        echo "  • ArgoCD: https://argo.jclee.me/applications/blacklist-production"
    else
        echo -e "${RED}❌ 배포 실패 - 로그를 확인하세요${NC}"
        kubectl logs -l app=blacklist -n default --tail=50
    fi
}

# 메인 실행
main() {
    echo -e "${BLUE}"
    echo "=================================================="
    echo "🔐 Blacklist K8s Secret 관리 스크립트"
    echo "=================================================="
    echo -e "${NC}"
    
    check_prerequisites
    backup_existing_secret
    get_secret_values
    update_secret
    trigger_argocd_sync
    check_deployment_status
    
    echo -e "${GREEN}"
    echo "=================================================="
    echo "✅ Secret 업데이트 및 배포 완료"
    echo "=================================================="
    echo -e "${NC}"
}

# 스크립트가 직접 실행될 때만 main 함수 호출
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi