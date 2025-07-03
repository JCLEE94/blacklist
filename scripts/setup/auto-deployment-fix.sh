#!/bin/bash

# Auto Deployment Fix Script
# 자동 배포 실패 방지를 위한 시스템 설정 스크립트

set -euo pipefail

echo "🔧 Auto Deployment Fix Setup"
echo "============================"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="blacklist"
REGISTRY="registry.jclee.me"
GITHUB_REPO="JCLEE94/blacklist"

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "error") echo -e "${RED}❌ $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️ $message${NC}" ;;
        "info") echo -e "${BLUE}ℹ️ $message${NC}" ;;
    esac
}

# 1. GitHub Secrets 검증 및 설정
setup_github_secrets() {
    echo ""
    echo "1️⃣ GitHub Secrets Configuration"
    echo "--------------------------------"
    
    # 필수 secrets 목록
    local required_secrets=(
        "DOCKER_USERNAME"
        "DOCKER_PASSWORD"
        "REGISTRY_USERNAME"
        "REGISTRY_PASSWORD"
    )
    
    # GitHub CLI 설치 확인
    if ! command -v gh &> /dev/null; then
        print_status "warning" "GitHub CLI not installed. Install it first:"
        echo "  brew install gh  # macOS"
        echo "  sudo apt install gh  # Ubuntu/Debian"
        return 1
    fi
    
    # GitHub 인증 확인
    if ! gh auth status &> /dev/null; then
        print_status "error" "Not authenticated with GitHub. Run: gh auth login"
        return 1
    fi
    
    # Secrets 확인 및 설정
    for secret in "${required_secrets[@]}"; do
        if gh secret list | grep -q "^$secret"; then
            print_status "success" "$secret is already set"
        else
            print_status "warning" "$secret is not set"
            
            # 환경변수에서 값 확인
            local env_value=""
            case $secret in
                "DOCKER_USERNAME") env_value="${DOCKER_USERNAME:-}" ;;
                "DOCKER_PASSWORD") env_value="${DOCKER_PASSWORD:-}" ;;
                "REGISTRY_USERNAME") env_value="${REGISTRY_USERNAME:-${DOCKER_USERNAME:-}}" ;;
                "REGISTRY_PASSWORD") env_value="${REGISTRY_PASSWORD:-${DOCKER_PASSWORD:-}}" ;;
            esac
            
            if [ -n "$env_value" ]; then
                echo "Setting $secret from environment variable..."
                echo "$env_value" | gh secret set "$secret"
                print_status "success" "$secret has been set"
            else
                print_status "error" "$secret needs to be set manually"
                echo "  Run: gh secret set $secret"
            fi
        fi
    done
}

# 2. Docker Registry 연결 테스트
test_docker_registry() {
    echo ""
    echo "2️⃣ Docker Registry Connection Test"
    echo "-----------------------------------"
    
    # Docker 로그인 테스트
    if [ -n "${DOCKER_USERNAME:-}" ] && [ -n "${DOCKER_PASSWORD:-}" ]; then
        echo "Testing Docker Hub login..."
        if echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin &> /dev/null; then
            print_status "success" "Docker Hub login successful"
        else
            print_status "error" "Docker Hub login failed"
        fi
    fi
    
    # Private Registry 로그인 테스트
    if [ -n "${REGISTRY_USERNAME:-}" ] && [ -n "${REGISTRY_PASSWORD:-}" ]; then
        echo "Testing private registry login..."
        if echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY" -u "$REGISTRY_USERNAME" --password-stdin &> /dev/null; then
            print_status "success" "Private registry login successful"
        else
            print_status "error" "Private registry login failed"
        fi
    fi
}

# 3. Kubernetes 설정 확인
check_kubernetes_setup() {
    echo ""
    echo "3️⃣ Kubernetes Configuration Check"
    echo "---------------------------------"
    
    # kubectl 설치 확인
    if ! command -v kubectl &> /dev/null; then
        print_status "error" "kubectl not installed"
        return 1
    fi
    
    # 클러스터 연결 확인
    if kubectl cluster-info &> /dev/null; then
        print_status "success" "Kubernetes cluster is accessible"
    else
        print_status "error" "Cannot connect to Kubernetes cluster"
        return 1
    fi
    
    # Namespace 확인
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        print_status "success" "Namespace '$NAMESPACE' exists"
    else
        print_status "warning" "Namespace '$NAMESPACE' not found, creating..."
        kubectl create namespace "$NAMESPACE"
        print_status "success" "Namespace created"
    fi
    
    # Registry secret 확인
    if kubectl get secret regcred -n "$NAMESPACE" &> /dev/null; then
        print_status "success" "Registry secret exists"
    else
        print_status "warning" "Registry secret not found, creating..."
        if [ -n "${REGISTRY_USERNAME:-}" ] && [ -n "${REGISTRY_PASSWORD:-}" ]; then
            kubectl create secret docker-registry regcred \
                --docker-server="$REGISTRY" \
                --docker-username="$REGISTRY_USERNAME" \
                --docker-password="$REGISTRY_PASSWORD" \
                -n "$NAMESPACE"
            print_status "success" "Registry secret created"
        else
            print_status "error" "Cannot create registry secret - credentials not provided"
        fi
    fi
}

# 4. Auto-updater 설정
setup_auto_updater() {
    echo ""
    echo "4️⃣ Auto-updater Configuration"
    echo "------------------------------"
    
    # Auto-updater CronJob 확인
    if kubectl get cronjob -n "$NAMESPACE" | grep -q "auto-updater"; then
        print_status "success" "Auto-updater CronJob exists"
    else
        print_status "warning" "Auto-updater CronJob not found"
        
        # auto-updater.yaml 파일 생성
        cat > /tmp/auto-updater.yaml <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: auto-updater
  namespace: $NAMESPACE
spec:
  schedule: "*/5 * * * *"  # 5분마다 실행
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: default
          containers:
          - name: updater
            image: alpine/k8s:1.28.4
            command:
            - /bin/sh
            - -c
            - |
              echo "🔄 Checking for new images..."
              
              # 현재 이미지 확인
              CURRENT_IMAGE=\$(kubectl get deployment blacklist -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')
              echo "Current image: \$CURRENT_IMAGE"
              
              # Registry에서 최신 태그 확인
              LATEST_TAG=\$(curl -s -u "$REGISTRY_USERNAME:$REGISTRY_PASSWORD" https://$REGISTRY/v2/blacklist/tags/list | grep -o '"[a-f0-9]\{7\}"' | sort -r | head -1 | tr -d '"')
              
              if [ -n "\$LATEST_TAG" ]; then
                NEW_IMAGE="$REGISTRY/blacklist:\$LATEST_TAG"
                
                if [ "\$CURRENT_IMAGE" != "\$NEW_IMAGE" ]; then
                  echo "🚀 New image found: \$NEW_IMAGE"
                  kubectl set image deployment/blacklist blacklist=\$NEW_IMAGE -n $NAMESPACE
                  kubectl rollout status deployment/blacklist -n $NAMESPACE --timeout=300s
                  echo "✅ Deployment updated successfully"
                else
                  echo "✅ Already running latest version"
                fi
              else
                echo "⚠️ Could not determine latest tag"
              fi
          restartPolicy: OnFailure
EOF
        
        kubectl apply -f /tmp/auto-updater.yaml
        print_status "success" "Auto-updater CronJob created"
        rm -f /tmp/auto-updater.yaml
    fi
}

# 5. 모니터링 설정
setup_monitoring() {
    echo ""
    echo "5️⃣ Monitoring Setup"
    echo "-------------------"
    
    # Health check endpoint 테스트
    NODE_PORT=$(kubectl get svc blacklist-nodeport -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "32541")
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "localhost")
    
    if [ -n "$NODE_IP" ] && [ -n "$NODE_PORT" ]; then
        HEALTH_URL="http://$NODE_IP:$NODE_PORT/health"
        echo "Testing health endpoint: $HEALTH_URL"
        
        if curl -f -s --connect-timeout 5 "$HEALTH_URL" &> /dev/null; then
            print_status "success" "Health endpoint is accessible"
        else
            print_status "warning" "Health endpoint not accessible"
        fi
    fi
    
    # GitHub Actions 워크플로우 상태 확인
    echo "Checking GitHub Actions workflow..."
    if [ -f ".github/workflows/k8s-deploy.yml" ]; then
        print_status "success" "K8s deployment workflow exists"
        echo "  It will automatically deploy on push to main branch"
    else
        print_status "warning" "K8s deployment workflow not found"
    fi
}

# 6. 자동 복구 스크립트 생성
create_recovery_script() {
    echo ""
    echo "6️⃣ Creating Recovery Script"
    echo "---------------------------"
    
    cat > /tmp/blacklist-recovery.sh <<'EOF'
#!/bin/bash
# Blacklist Deployment Recovery Script

NAMESPACE="blacklist"

echo "🚑 Starting Blacklist Recovery..."

# 1. Fix PVC issues
echo "Checking PVCs..."
PENDING_PVCS=$(kubectl get pvc -n $NAMESPACE -o json | jq -r '.items[] | select(.status.phase=="Pending") | .metadata.name')

if [ -n "$PENDING_PVCS" ]; then
    echo "Found pending PVCs: $PENDING_PVCS"
    for PVC in $PENDING_PVCS; do
        PV_NAME="${PVC}-pv"
        kubectl patch pv "$PV_NAME" -p '{"spec":{"claimRef": null}}' 2>/dev/null || true
    done
    
    kubectl delete pvc $PENDING_PVCS -n $NAMESPACE --force --grace-period=0
    sleep 5
fi

# 2. Reapply Kubernetes manifests
echo "Reapplying Kubernetes manifests..."
kubectl apply -k k8s/

# 3. Force image update
echo "Forcing deployment restart..."
kubectl rollout restart deployment/blacklist -n $NAMESPACE
kubectl rollout status deployment/blacklist -n $NAMESPACE --timeout=300s

# 4. Verify health
sleep 10
NODE_PORT=$(kubectl get svc blacklist-nodeport -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

if curl -f -s "http://$NODE_IP:$NODE_PORT/health" > /dev/null 2>&1; then
    echo "✅ Recovery successful - service is healthy"
else
    echo "❌ Recovery failed - service still unhealthy"
    exit 1
fi
EOF
    
    chmod +x /tmp/blacklist-recovery.sh
    
    if [ -d "scripts/recovery" ]; then
        mv /tmp/blacklist-recovery.sh scripts/recovery/
        print_status "success" "Recovery script created at scripts/recovery/blacklist-recovery.sh"
    else
        mkdir -p scripts/recovery
        mv /tmp/blacklist-recovery.sh scripts/recovery/
        print_status "success" "Recovery script created"
    fi
}

# 7. 환경 변수 템플릿 생성
create_env_template() {
    echo ""
    echo "7️⃣ Creating Environment Template"
    echo "--------------------------------"
    
    cat > .env.example <<EOF
# Docker Registry Credentials
DOCKER_USERNAME=your_docker_username
DOCKER_PASSWORD=your_docker_password

# Private Registry Credentials (if different from Docker Hub)
REGISTRY_USERNAME=your_registry_username
REGISTRY_PASSWORD=your_registry_password

# Deployment Configuration
NAMESPACE=blacklist
REGISTRY=registry.jclee.me

# Alert Webhook (optional)
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
DEPLOYMENT_WEBHOOK_URL=https://your-webhook-endpoint.com

# Application Credentials
REGTECH_USERNAME=nextrade
REGTECH_PASSWORD=Sprtmxm1@3
SECUDIUM_USERNAME=nextrade
SECUDIUM_PASSWORD=Sprtmxm1@3
EOF
    
    print_status "success" "Environment template created at .env.example"
    
    if [ ! -f ".env" ]; then
        print_status "info" "Copy .env.example to .env and fill in your credentials"
    fi
}

# Main execution
main() {
    echo "Starting auto deployment fix setup..."
    echo ""
    
    # Load environment variables if .env exists
    if [ -f ".env" ]; then
        source .env
        print_status "info" "Loaded environment variables from .env"
    fi
    
    # Run all setup functions
    setup_github_secrets
    test_docker_registry
    check_kubernetes_setup
    setup_auto_updater
    setup_monitoring
    create_recovery_script
    create_env_template
    
    echo ""
    echo "========================================="
    echo "✅ Auto Deployment Fix Setup Complete!"
    echo "========================================="
    echo ""
    echo "Next steps:"
    echo "1. Ensure all GitHub secrets are properly set"
    echo "2. Test deployment with: git push origin main"
    echo "3. Monitor deployment: kubectl logs -n blacklist deployment/blacklist -f"
    echo "4. Check auto-updater: kubectl get cronjob -n blacklist"
    echo ""
    echo "Recovery script available at: scripts/recovery/blacklist-recovery.sh"
    echo ""
}

# Run main function
main "$@"