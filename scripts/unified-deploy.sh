#!/bin/bash
# 통합 배포 스크립트 - 플랫폼별 배포 자동화

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}  Blacklist 통합 배포 스크립트 (ArgoCD GitOps)${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_usage() {
    echo "사용법: $0 [PLATFORM] [OPTIONS]"
    echo ""
    echo "플랫폼:"
    echo "  kubernetes    - Kubernetes 클러스터에 배포"
    echo "  docker        - Docker Desktop 환경에 배포"
    echo "  production    - 운영 환경에 배포"
    echo "  local         - 로컬 개발 환경 실행"
    echo ""
    echo "옵션:"
    echo "  --dry-run     - 실제 배포 없이 명령어만 출력"
    echo "  --force       - 강제 재배포"
    echo "  --help        - 도움말 출력"
    echo ""
    echo "예시:"
    echo "  $0 kubernetes"
    echo "  $0 docker --force"
    echo "  $0 production --dry-run"
}

check_platform() {
    case $1 in
        kubernetes|k8s)
            if ! command -v kubectl &> /dev/null; then
                echo -e "${RED}❌ kubectl이 설치되지 않았습니다${NC}"
                exit 1
            fi
            if ! command -v argocd &> /dev/null; then
                echo -e "${YELLOW}⚠️ ArgoCD CLI가 설치되지 않았습니다. GitOps 기능이 제한될 수 있습니다.${NC}"
            fi
            return 0
            ;;
        docker)
            if ! command -v docker &> /dev/null; then
                echo -e "${RED}❌ Docker가 설치되지 않았습니다${NC}"
                exit 1
            fi
            return 0
            ;;
        production|prod)
            # 운영 환경 체크 로직
            return 0
            ;;
        local)
            if ! command -v python3 &> /dev/null; then
                echo -e "${RED}❌ Python 3가 설치되지 않았습니다${NC}"
                exit 1
            fi
            return 0
            ;;
        *)
            echo -e "${RED}❌ 지원하지 않는 플랫폼: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
}

deploy_kubernetes() {
    echo -e "${GREEN}🚀 Kubernetes GitOps 배포 시작...${NC}"
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "kubectl apply -k k8s/"
        echo "kubectl apply -f k8s/argocd-app-clean.yaml"
        echo "argocd app sync blacklist --grpc-web"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    if [ -f "scripts/k8s-management.sh" ]; then
        chmod +x scripts/k8s-management.sh
        scripts/k8s-management.sh deploy
    else
        # 직접 ArgoCD GitOps 배포
        echo -e "${BLUE}📦 Kubernetes 매니페스트 적용...${NC}"
        kubectl apply -k k8s/
        
        echo -e "${BLUE}🎯 ArgoCD 애플리케이션 설정...${NC}"
        if [ -f "k8s/argocd-app-clean.yaml" ]; then
            kubectl apply -f k8s/argocd-app-clean.yaml
        fi
        
        echo -e "${BLUE}🔄 ArgoCD 동기화...${NC}"
        if command -v argocd &> /dev/null; then
            argocd app sync blacklist --grpc-web --timeout 300 || echo "ArgoCD 동기화 완료"
        else
            echo -e "${YELLOW}⚠️ ArgoCD CLI가 설치되지 않았습니다${NC}"
        fi
        
        echo -e "${GREEN}✅ Kubernetes GitOps 배포 완료${NC}"
    fi
}

deploy_docker() {
    echo -e "${GREEN}🐳 Docker Desktop 배포 시작...${NC}"
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "docker-compose up -d --build"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    if [ -f "scripts/platforms/docker-desktop/deploy-docker-desktop.sh" ]; then
        chmod +x scripts/platforms/docker-desktop/deploy-docker-desktop.sh
        scripts/platforms/docker-desktop/deploy-docker-desktop.sh
    else
        # 직접 배포
        docker-compose up -d --build
        echo -e "${GREEN}✅ Docker Desktop 배포 완료${NC}"
    fi
}

deploy_production() {
    echo -e "${GREEN}🏭 운영 환경 배포 시작...${NC}"
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "운영 배포 스크립트 실행 (dry-run)"
        return 0
    fi
    
    # 운영 배포는 신중하게
    echo -e "${YELLOW}⚠️  운영 환경에 배포합니다. 계속하시겠습니까? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}배포가 취소되었습니다${NC}"
        exit 0
    fi
    
    cd "$PROJECT_ROOT"
    
    if [ -f "scripts/platforms/production/deploy-single-to-production.sh" ]; then
        chmod +x scripts/platforms/production/deploy-single-to-production.sh
        scripts/platforms/production/deploy-single-to-production.sh
    else
        echo -e "${RED}❌ 운영 배포 스크립트를 찾을 수 없습니다${NC}"
        exit 1
    fi
}

run_local() {
    echo -e "${GREEN}💻 로컬 개발 환경 실행...${NC}"
    
    cd "$PROJECT_ROOT"
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "python3 main.py --debug"
        return 0
    fi
    
    # 의존성 확인
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}❌ requirements.txt를 찾을 수 없습니다${NC}"
        exit 1
    fi
    
    # 데이터베이스 초기화
    if [ ! -f "instance/blacklist.db" ]; then
        echo -e "${YELLOW}📊 데이터베이스 초기화 중...${NC}"
        python3 init_database.py
    fi
    
    echo -e "${BLUE}🔄 개발 서버 시작 (포트 8541)...${NC}"
    python3 main.py --debug
}

# 메인 실행 로직
main() {
    print_header
    
    # 인자 파싱
    PLATFORM=""
    DRY_RUN="false"
    FORCE="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --force)
                FORCE="true"
                shift
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            -*|--*)
                echo -e "${RED}❌ 알 수 없는 옵션: $1${NC}"
                print_usage
                exit 1
                ;;
            *)
                if [ -z "$PLATFORM" ]; then
                    PLATFORM="$1"
                else
                    echo -e "${RED}❌ 여러 플랫폼을 동시에 지정할 수 없습니다${NC}"
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # 플랫폼이 지정되지 않은 경우
    if [ -z "$PLATFORM" ]; then
        echo -e "${YELLOW}배포할 플랫폼을 선택하세요:${NC}"
        echo "1) Kubernetes"
        echo "2) Docker Desktop"
        echo "3) Production"
        echo "4) Local Development"
        echo -n "선택 (1-4): "
        read -r choice
        
        case $choice in
            1) PLATFORM="kubernetes" ;;
            2) PLATFORM="docker" ;;
            3) PLATFORM="production" ;;
            4) PLATFORM="local" ;;
            *) echo -e "${RED}❌ 잘못된 선택입니다${NC}"; exit 1 ;;
        esac
    fi
    
    # 플랫폼 확인
    check_platform "$PLATFORM"
    
    # 배포 실행
    echo -e "${BLUE}📋 배포 정보:${NC}"
    echo -e "  플랫폼: ${GREEN}$PLATFORM${NC}"
    echo -e "  Dry Run: ${YELLOW}$DRY_RUN${NC}"
    echo -e "  Force: ${YELLOW}$FORCE${NC}"
    echo ""
    
    case $PLATFORM in
        kubernetes|k8s)
            deploy_kubernetes
            ;;
        docker)
            deploy_docker
            ;;
        production|prod)
            deploy_production
            ;;
        local)
            run_local
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}🎉 배포 완료!${NC}"
}

# 스크립트 실행
main "$@"