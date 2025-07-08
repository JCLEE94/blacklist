#!/bin/bash
# Cloudflare Tunnel Kubernetes 설정 스크립트
# NodePort 서비스를 Cloudflare Zero Trust를 통해 외부에 노출

echo "🌐 Cloudflare Tunnel Kubernetes 설정 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 기본값 설정
NAMESPACE="${NAMESPACE:-blacklist}"
CLOUDFLARE_TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-eyJhIjoiYThkOWM2N2Y1ODZhY2RkMTVlZWJjYzY1Y2EzYWE1YmIiLCJ0IjoiOGVhNzg5MDYtMWEwNS00NGZiLWExYmItZTUxMjE3MmNiNWFiIiwicyI6Ill6RXlZVEUwWWpRdE1tVXlNUzAwWmpRMExXSTVaR0V0WkdNM09UY3pOV1ExT1RGbSJ9}"
CLOUDFLARE_HOSTNAME="${CLOUDFLARE_HOSTNAME:-blacklist.jclee.me}"
NODE_PORT="${NODE_PORT:-32452}"
SERVICE_NAME="${SERVICE_NAME:-blacklist-nodeport}"

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 사전 요구사항 확인
check_requirements() {
    print_step "사전 요구사항 확인 중..."
    
    # kubectl 확인
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl이 설치되지 않았습니다."
        exit 1
    fi
    
    # 네임스페이스 확인
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        print_error "네임스페이스 $NAMESPACE가 존재하지 않습니다."
        exit 1
    fi
    
    # NodePort 서비스 확인
    if ! kubectl get svc $SERVICE_NAME -n $NAMESPACE &> /dev/null; then
        print_error "서비스 $SERVICE_NAME가 $NAMESPACE 네임스페이스에 존재하지 않습니다."
        exit 1
    fi
    
    print_success "사전 요구사항 확인 완료"
}

# Cloudflare Tunnel 토큰 설정
setup_tunnel_token() {
    print_step "Cloudflare Tunnel 토큰 설정 중..."
    
    if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
        print_warning "CLOUDFLARE_TUNNEL_TOKEN 환경 변수가 설정되지 않았습니다."
        echo ""
        echo "Cloudflare Zero Trust 대시보드에서 터널을 생성하고 토큰을 받아주세요:"
        echo "1. https://one.dash.cloudflare.com/ 접속"
        echo "2. Access > Tunnels 메뉴로 이동"
        echo "3. 'Create a tunnel' 클릭"
        echo "4. 터널 이름 입력 (예: blacklist-tunnel)"
        echo "5. 생성된 토큰을 복사"
        echo ""
        echo -n "터널 토큰을 입력하세요: "
        read -r CLOUDFLARE_TUNNEL_TOKEN
        
        if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
            print_error "터널 토큰이 필요합니다."
            exit 1
        fi
    fi
    
    # Secret 생성 또는 업데이트
    print_step "Kubernetes Secret 생성 중..."
    kubectl create secret generic cloudflared-secret \
        --from-literal=token="$CLOUDFLARE_TUNNEL_TOKEN" \
        -n $NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    print_success "터널 토큰 설정 완료"
}

# ConfigMap 생성
create_configmap() {
    print_step "ConfigMap 생성 중..."
    
    # NodePort 정보 가져오기
    ACTUAL_NODE_PORT=$(kubectl get svc $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')
    if [ -n "$ACTUAL_NODE_PORT" ]; then
        NODE_PORT=$ACTUAL_NODE_PORT
    fi
    
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: cloudflared-config
  namespace: $NAMESPACE
data:
  config.yaml: |
    tunnel: blacklist-tunnel
    credentials-file: /etc/cloudflared/creds/token
    
    ingress:
      # Blacklist 서비스로 라우팅
      - hostname: $CLOUDFLARE_HOSTNAME
        service: http://$SERVICE_NAME:2541
      # 기본 404 응답
      - service: http_status:404
EOF
    
    print_success "ConfigMap 생성 완료"
}

# Cloudflared Deployment 적용
deploy_cloudflared() {
    print_step "Cloudflared Deployment 적용 중..."
    
    # cloudflared-deployment.yaml 파일이 있으면 사용, 없으면 인라인 생성
    if [ -f "k8s/cloudflared-deployment.yaml" ]; then
        # Secret 토큰 업데이트 후 적용
        kubectl apply -f k8s/cloudflared-deployment.yaml
    else
        # 인라인 Deployment 생성
        cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudflared
  namespace: $NAMESPACE
  labels:
    app: cloudflared
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cloudflared
  template:
    metadata:
      labels:
        app: cloudflared
    spec:
      containers:
      - name: cloudflared
        image: cloudflare/cloudflared:latest
        args:
        - tunnel
        - --no-autoupdate
        - run
        - --token
        - \$(TUNNEL_TOKEN)
        env:
        - name: TUNNEL_TOKEN
          valueFrom:
            secretKeyRef:
              name: cloudflared-secret
              key: token
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /ready
            port: 2000
          initialDelaySeconds: 10
          periodSeconds: 10
EOF
    fi
    
    print_success "Cloudflared Deployment 적용 완료"
}

# 배포 확인
verify_deployment() {
    print_step "배포 확인 중..."
    
    # Pod 준비 대기
    echo "Pod 시작 대기 중..."
    kubectl wait --for=condition=ready pod -l app=cloudflared -n $NAMESPACE --timeout=300s
    
    # Pod 상태 확인
    print_step "Pod 상태:"
    kubectl get pods -l app=cloudflared -n $NAMESPACE
    
    # 로그 확인
    print_step "최근 로그:"
    kubectl logs -l app=cloudflared -n $NAMESPACE --tail=20
    
    print_success "배포 확인 완료"
}

# 접속 정보 출력
print_access_info() {
    echo ""
    echo "====================================="
    echo "✅ Cloudflare Tunnel 설정 완료!"
    echo "====================================="
    echo "🌐 외부 접속 URL: https://$CLOUDFLARE_HOSTNAME"
    echo "🔧 내부 NodePort: $NODE_PORT"
    echo "📊 터널 상태: https://one.dash.cloudflare.com/"
    echo "====================================="
    echo ""
    echo "유용한 명령어:"
    echo "- Pod 상태: kubectl get pods -l app=cloudflared -n $NAMESPACE"
    echo "- 로그 확인: kubectl logs -l app=cloudflared -n $NAMESPACE -f"
    echo "- 재시작: kubectl rollout restart deployment/cloudflared -n $NAMESPACE"
    echo "- 삭제: kubectl delete deployment cloudflared -n $NAMESPACE"
}

# 메인 실행
main() {
    echo "======================================"
    echo "Cloudflare Tunnel Kubernetes 설정"
    echo "======================================"
    echo ""
    
    # 환경 변수 출력
    echo "설정:"
    echo "  네임스페이스: $NAMESPACE"
    echo "  서비스: $SERVICE_NAME"
    echo "  NodePort: $NODE_PORT"
    echo "  호스트명: $CLOUDFLARE_HOSTNAME"
    echo ""
    
    # 실행 단계
    check_requirements
    setup_tunnel_token
    create_configmap
    deploy_cloudflared
    verify_deployment
    print_access_info
}

# 명령행 인자 처리
case "${1:-deploy}" in
    deploy)
        main
        ;;
    delete|remove)
        print_step "Cloudflare Tunnel 삭제 중..."
        kubectl delete deployment cloudflared -n $NAMESPACE || true
        kubectl delete configmap cloudflared-config -n $NAMESPACE || true
        kubectl delete secret cloudflared-secret -n $NAMESPACE || true
        print_success "Cloudflare Tunnel 삭제 완료"
        ;;
    status)
        print_step "Cloudflare Tunnel 상태:"
        kubectl get deployment cloudflared -n $NAMESPACE
        kubectl get pods -l app=cloudflared -n $NAMESPACE
        ;;
    logs)
        kubectl logs -l app=cloudflared -n $NAMESPACE -f
        ;;
    *)
        echo "사용법: $0 [deploy|delete|status|logs]"
        exit 1
        ;;
esac