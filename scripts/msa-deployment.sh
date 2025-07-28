#!/bin/bash

# MSA 배포 스크립트
# Blacklist Management System을 마이크로서비스로 배포

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
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

# 환경 변수 체크
check_environment() {
    log_info "환경 변수 확인 중..."
    
    required_vars=(
        "REGTECH_USERNAME"
        "REGTECH_PASSWORD" 
        "SECUDIUM_USERNAME"
        "SECUDIUM_PASSWORD"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "다음 환경 변수가 설정되지 않았습니다:"
        printf '%s\n' "${missing_vars[@]}"
        log_info "scripts/load-env.sh를 실행하여 환경 변수를 로드하세요."
        exit 1
    fi
    
    log_success "모든 필수 환경 변수가 설정되었습니다."
}

# Docker 이미지 빌드
build_images() {
    log_info "Docker 이미지 빌드 중..."
    
    services=("collection-service" "blacklist-service" "analytics-service" "api-gateway")
    
    for service in "${services[@]}"; do
        log_info "$service 이미지 빌드 중..."
        if docker build -t "blacklist/$service:latest" "./services/$service/"; then
            log_success "$service 이미지 빌드 완료"
        else
            log_error "$service 이미지 빌드 실패"
            exit 1
        fi
    done
}

# Dockerfile 생성
create_dockerfiles() {
    log_info "Dockerfile 생성 중..."
    
    services=("collection-service" "blacklist-service" "analytics-service" "api-gateway")
    
    for service in "${services[@]}"; do
        dockerfile_path="./services/$service/Dockerfile"
        
        if [[ ! -f "$dockerfile_path" ]]; then
            log_info "$service용 Dockerfile 생성 중..."
            
            cat > "$dockerfile_path" << EOF
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 비root 사용자 생성
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["python", "app.py"]
EOF
            
            # requirements.txt 생성
            cat > "./services/$service/requirements.txt" << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
httpx==0.25.2
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
redis==5.0.1
pandas==2.1.4
numpy==1.24.4
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
openpyxl==3.1.2
beautifulsoup4==4.12.2
requests==2.31.0
aiofiles==0.24.0
EOF
        fi
    done
    
    log_success "Dockerfile 생성 완료"
}

# Docker Compose 배포
deploy_docker_compose() {
    log_info "Docker Compose로 MSA 배포 중..."
    
    # .env 파일 생성
    cat > .env << EOF
REGTECH_USERNAME=${REGTECH_USERNAME}
REGTECH_PASSWORD=${REGTECH_PASSWORD}
SECUDIUM_USERNAME=${SECUDIUM_USERNAME}
SECUDIUM_PASSWORD=${SECUDIUM_PASSWORD}
JWT_SECRET_KEY=${JWT_SECRET_KEY:-$(openssl rand -base64 32)}
EOF
    
    # Docker Compose 실행
    if docker-compose -f docker-compose.msa.yml up -d; then
        log_success "MSA 컨테이너 배포 완료"
    else
        log_error "MSA 컨테이너 배포 실패"
        exit 1
    fi
}

# Kubernetes 배포
deploy_kubernetes() {
    log_info "Kubernetes로 MSA 배포 중..."
    
    # 네임스페이스 생성
    kubectl apply -f k8s/msa/namespace.yaml
    
    # ConfigMap과 Secret 업데이트
    kubectl delete configmap blacklist-config -n blacklist-msa --ignore-not-found
    kubectl delete secret blacklist-secrets -n blacklist-msa --ignore-not-found
    
    # 환경 변수를 Secret으로 생성
    kubectl create secret generic blacklist-secrets -n blacklist-msa \
        --from-literal=DB_USER="blacklist_user" \
        --from-literal=DB_PASSWORD="blacklist_pass123" \
        --from-literal=REGTECH_USERNAME="${REGTECH_USERNAME}" \
        --from-literal=REGTECH_PASSWORD="${REGTECH_PASSWORD}" \
        --from-literal=SECUDIUM_USERNAME="${SECUDIUM_USERNAME}" \
        --from-literal=SECUDIUM_PASSWORD="${SECUDIUM_PASSWORD}" \
        --from-literal=JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(openssl rand -base64 32)}"
    
    # ConfigMap 적용
    kubectl apply -f k8s/msa/configmap.yaml
    
    # 데이터베이스 배포
    kubectl apply -f k8s/msa/postgres-deployment.yaml
    kubectl apply -f k8s/msa/redis-deployment.yaml
    
    # 데이터베이스 준비 대기
    log_info "데이터베이스 서비스 준비 대기 중..."
    kubectl wait --for=condition=ready pod -l app=postgres -n blacklist-msa --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n blacklist-msa --timeout=300s
    
    # 마이크로서비스 배포
    kubectl apply -f k8s/msa/services-deployment.yaml
    
    # 서비스 준비 대기
    log_info "마이크로서비스 준비 대기 중..."
    kubectl wait --for=condition=ready pod -l app=collection-service -n blacklist-msa --timeout=300s
    kubectl wait --for=condition=ready pod -l app=blacklist-service -n blacklist-msa --timeout=300s
    kubectl wait --for=condition=ready pod -l app=analytics-service -n blacklist-msa --timeout=300s
    kubectl wait --for=condition=ready pod -l app=api-gateway -n blacklist-msa --timeout=300s
    
    log_success "Kubernetes MSA 배포 완료"
}

# 배포 상태 확인
check_deployment_status() {
    log_info "배포 상태 확인 중..."
    
    if [[ "$1" == "k8s" ]]; then
        echo ""
        log_info "=== Kubernetes 배포 상태 ==="
        kubectl get pods -n blacklist-msa
        kubectl get services -n blacklist-msa
        
        # API Gateway 접속 정보
        gateway_ip=$(kubectl get service api-gateway -n blacklist-msa -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
        if [[ "$gateway_ip" != "pending" ]]; then
            log_success "API Gateway 접속: http://$gateway_ip:8080"
        else
            log_info "API Gateway LoadBalancer IP 할당 대기 중..."
            log_info "포트포워딩으로 접속: kubectl port-forward service/api-gateway 8080:8080 -n blacklist-msa"
        fi
    else
        echo ""
        log_info "=== Docker Compose 배포 상태 ==="
        docker-compose -f docker-compose.msa.yml ps
        
        log_success "API Gateway 접속: http://localhost:8080"
    fi
    
    echo ""
    log_info "=== 서비스 엔드포인트 ==="
    echo "• API 문서: http://localhost:8080/docs"
    echo "• 헬스체크: http://localhost:8080/health"
    echo "• 블랙리스트 조회: http://localhost:8080/api/v1/blacklist/active"
    echo "• FortiGate 형식: http://localhost:8080/api/v1/blacklist/fortigate"
    echo "• 분석 리포트: http://localhost:8080/api/v1/analytics/report"
}

# 서비스 테스트
test_services() {
    log_info "서비스 기능 테스트 중..."
    
    base_url="http://localhost:8080"
    
    # 헬스체크
    if curl -sf "$base_url/health" > /dev/null; then
        log_success "API Gateway 헬스체크 통과"
    else
        log_error "API Gateway 헬스체크 실패"
        return 1
    fi
    
    # 블랙리스트 서비스 테스트
    if curl -sf "$base_url/api/v1/blacklist/statistics" > /dev/null; then
        log_success "블랙리스트 서비스 정상"
    else
        log_warning "블랙리스트 서비스 응답 없음 (초기화 중일 수 있음)"
    fi
    
    # 분석 서비스 테스트
    if curl -sf "$base_url/api/v1/analytics/realtime" > /dev/null; then
        log_success "분석 서비스 정상"
    else
        log_warning "분석 서비스 응답 없음"
    fi
    
    log_success "서비스 테스트 완료"
}

# 로그 확인
show_logs() {
    if [[ "$1" == "k8s" ]]; then
        log_info "Kubernetes 로그 확인:"
        echo "kubectl logs -f deployment/api-gateway -n blacklist-msa"
        echo "kubectl logs -f deployment/blacklist-service -n blacklist-msa"
        echo "kubectl logs -f deployment/collection-service -n blacklist-msa"
        echo "kubectl logs -f deployment/analytics-service -n blacklist-msa"
    else
        log_info "Docker Compose 로그 확인:"
        echo "docker-compose -f docker-compose.msa.yml logs -f api-gateway"
        echo "docker-compose -f docker-compose.msa.yml logs -f blacklist-service"
        echo "docker-compose -f docker-compose.msa.yml logs -f collection-service"
        echo "docker-compose -f docker-compose.msa.yml logs -f analytics-service"
    fi
}

# 정리 함수
cleanup() {
    if [[ "$1" == "k8s" ]]; then
        log_info "Kubernetes 리소스 정리 중..."
        kubectl delete namespace blacklist-msa --ignore-not-found
    else
        log_info "Docker Compose 정리 중..."
        docker-compose -f docker-compose.msa.yml down -v
    fi
    log_success "정리 완료"
}

# 메인 함수
main() {
    case "${1:-}" in
        "build")
            check_environment
            create_dockerfiles
            build_images
            ;;
        "deploy-docker")
            check_environment
            create_dockerfiles
            build_images
            deploy_docker_compose
            sleep 30  # 서비스 시작 대기
            check_deployment_status "docker"
            test_services
            show_logs "docker"
            ;;
        "deploy-k8s")
            check_environment
            create_dockerfiles
            build_images
            deploy_kubernetes
            check_deployment_status "k8s"
            test_services
            show_logs "k8s"
            ;;
        "status")
            if kubectl get namespace blacklist-msa &> /dev/null; then
                check_deployment_status "k8s"
            else
                check_deployment_status "docker"
            fi
            ;;
        "test")
            test_services
            ;;
        "cleanup-docker")
            cleanup "docker"
            ;;
        "cleanup-k8s")
            cleanup "k8s"
            ;;
        *)
            echo "MSA 배포 스크립트"
            echo ""
            echo "사용법: $0 {build|deploy-docker|deploy-k8s|status|test|cleanup-docker|cleanup-k8s}"
            echo ""
            echo "명령어:"
            echo "  build          - Docker 이미지 빌드"
            echo "  deploy-docker  - Docker Compose로 배포"
            echo "  deploy-k8s     - Kubernetes로 배포"
            echo "  status         - 배포 상태 확인"
            echo "  test           - 서비스 기능 테스트"
            echo "  cleanup-docker - Docker Compose 리소스 정리"
            echo "  cleanup-k8s    - Kubernetes 리소스 정리"
            echo ""
            echo "배포 전 환경 변수 설정:"
            echo "  export REGTECH_USERNAME='your-username'"
            echo "  export REGTECH_PASSWORD='your-password'"
            echo "  export SECUDIUM_USERNAME='your-username'"
            echo "  export SECUDIUM_PASSWORD='your-password'"
            echo ""
            echo "또는 scripts/load-env.sh 실행"
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"