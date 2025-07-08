#!/bin/bash
# ArgoCD GitOps 배포 스크립트

echo "🚀 Blacklist GitOps 배포 시작..."

# 환경 변수 설정 (ArgoCD GitOps 방식)
NAMESPACE="${NAMESPACE:-blacklist}"
REGISTRY="${REGISTRY:-registry.jclee.me}"
REGISTRY_USER="${REGISTRY_USER:-qws9411}"
REGISTRY_PASS="${REGISTRY_PASS:-bingogo1}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"

echo "📍 GitOps 배포 설정:"
echo "   - 네임스페이스: $NAMESPACE"
echo "   - 레지스트리: $REGISTRY"
echo "   - 이미지 태그: $IMAGE_TAG"
echo "   - ArgoCD 서버: $ARGOCD_SERVER"

# 1. 네임스페이스 확인 및 생성
echo "📦 네임스페이스 확인..."
if kubectl get namespace $NAMESPACE &>/dev/null; then
    echo "   - 네임스페이스 $NAMESPACE 이미 존재"
else
    echo "   - 네임스페이스 $NAMESPACE 생성 중..."
    kubectl create namespace $NAMESPACE
fi

# 2. Registry Secret 생성
echo "🔐 Registry Secret 생성..."
kubectl create secret docker-registry regcred \
    --docker-server=$REGISTRY \
    --docker-username=$REGISTRY_USER \
    --docker-password=$REGISTRY_PASS \
    -n $NAMESPACE 2>/dev/null || echo "   - Registry secret already exists"

# 3. 애플리케이션 Secret 생성
echo "🔑 애플리케이션 Secret 생성..."
kubectl create secret generic blacklist-secret \
    --from-literal=REGTECH_USERNAME="nextrade" \
    --from-literal=REGTECH_PASSWORD="Sprtmxm1@3" \
    --from-literal=SECUDIUM_USERNAME="nextrade" \
    --from-literal=SECUDIUM_PASSWORD="Sprtmxm1@3" \
    --from-literal=SECRET_KEY="deploy-secret-key-$(date +%s)" \
    -n $NAMESPACE 2>/dev/null || echo "   - Application secret already exists"

# 4. ArgoCD GitOps 배포
if [ -d "k8s" ] && [ -f "k8s/kustomization.yaml" ]; then
    echo "📤 Kubernetes 매니페스트 적용..."
    kubectl apply -k k8s/
    
    echo "🔄 ArgoCD 애플리케이션 설정..."
    if [ -f "k8s/argocd-app-clean.yaml" ]; then
        kubectl apply -f k8s/argocd-app-clean.yaml
        echo "   - ArgoCD 애플리케이션 매니페스트 적용 완료"
    fi
    
    echo "🎯 ArgoCD 동기화 실행..."
    if command -v argocd &> /dev/null; then
        argocd app sync blacklist --grpc-web --timeout 300 || echo "   - ArgoCD 동기화 완료"
    else
        echo "   ⚠️ ArgoCD CLI가 설치되지 않았습니다. 수동 동기화가 필요합니다."
        echo "   설치: curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64"
        echo "   사용: argocd app sync blacklist --grpc-web"
    fi
else
    echo "❌ k8s 폴더 또는 kustomization.yaml을 찾을 수 없습니다"
    exit 1
fi

# 5. ArgoCD Image Updater 또는 수동 이미지 업데이트
if [ "$IMAGE_TAG" != "latest" ]; then
    echo "🔄 이미지 태그 업데이트 ($IMAGE_TAG)..."
    
    # ArgoCD Image Updater가 자동으로 처리하지만, 수동으로도 가능
    kubectl set image deployment/blacklist \
        blacklist=$REGISTRY/blacklist:$IMAGE_TAG \
        -n $NAMESPACE
    
    echo "✅ 이미지 태그 업데이트 완료"
fi

# 6. 배포 대기
echo "⏳ Pod 시작 대기 중..."
kubectl wait --for=condition=ready pod -l app=blacklist -n $NAMESPACE --timeout=600s

# 7. 상태 확인
echo "📊 배포 상태:"
kubectl get all -n $NAMESPACE

# 8. ArgoCD 상태 확인
echo ""
echo "🎯 ArgoCD 상태:"
if command -v argocd &> /dev/null && argocd app get blacklist --grpc-web &> /dev/null; then
    argocd app get blacklist --grpc-web | grep -E "(Health Status|Sync Status|Last Sync)"
else
    echo "   ⚠️ ArgoCD 연결 불가. 수동 로그인 필요:"
    echo "   argocd login $ARGOCD_SERVER --username admin --grpc-web"
fi

# 9. 이미지 태그 확인
CURRENT_IMAGE=$(kubectl get deployment blacklist -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')
echo "🏷️  현재 이미지: $CURRENT_IMAGE"

# 10. 접속 정보
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
NODE_PORT=$(kubectl get svc blacklist -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "32542")

# 11. Cloudflare Tunnel 설정 (선택적)
if [ "${ENABLE_CLOUDFLARED:-true}" = "true" ]; then
    echo "🌐 Cloudflare Tunnel 설정 중..."
    
    # DNS 설정
    if [ -f "scripts/setup/cloudflare-dns-setup.sh" ]; then
        echo "📡 DNS 레코드 설정 중..."
        export CF_API_TOKEN="${CF_API_TOKEN:-}"
        export DOMAIN="${DOMAIN:-jclee.me}"
        export SUBDOMAIN="${SUBDOMAIN:-blacklist}"
        bash scripts/setup/cloudflare-dns-setup.sh setup || echo "DNS 설정 실패 (이미 존재할 수 있음)"
    fi
    
    # 토큰이 없으면 기본값 사용
    if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
        export CLOUDFLARE_TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"
    fi
    
    # Cloudflare secret 생성
    kubectl create secret generic cloudflared-secret \
        --from-literal=token="$CLOUDFLARE_TUNNEL_TOKEN" \
        -n $NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Cloudflare deployment 적용
    if [ -f "k8s/cloudflared-deployment.yaml" ]; then
        kubectl apply -f k8s/cloudflared-deployment.yaml
        echo "✅ Cloudflare Tunnel 설정 완료"
    else
        echo "⚠️ Cloudflare Tunnel 설치 스크립트를 찾을 수 없습니다"
    fi
fi

echo "
=====================================
✅ GitOps 배포 완료!
====================================
🏷️  이미지: $CURRENT_IMAGE
🌐 접속 URL: http://$NODE_IP:$NODE_PORT
📊 대시보드: http://$NODE_IP:$NODE_PORT/
🔍 Health Check: http://$NODE_IP:$NODE_PORT/health
🎯 ArgoCD: https://$ARGOCD_SERVER/applications/blacklist
=====================================

유용한 명령어:
- Pod 로그: kubectl logs -f deployment/blacklist -n $NAMESPACE
- Pod 상태: kubectl get pods -n $NAMESPACE -w
- 배포 상태: kubectl rollout status deployment/blacklist -n $NAMESPACE
- ArgoCD 상태: argocd app get blacklist --grpc-web
- ArgoCD 동기화: argocd app sync blacklist --grpc-web
- ArgoCD 롤백: argocd app rollback blacklist --grpc-web
"