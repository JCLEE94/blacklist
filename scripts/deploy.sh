#!/bin/bash
# CI/CD 최적화된 배포 스크립트

echo "🚀 Blacklist 배포 시작..."

# 환경 변수 설정 (CI/CD에서 전달받거나 기본값 사용)
NAMESPACE="${NAMESPACE:-blacklist-new}"
REGISTRY="${REGISTRY:-registry.jclee.me}"
REGISTRY_USER="${REGISTRY_USER:-qws9411}"
REGISTRY_PASS="${REGISTRY_PASS:-bingogo1}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
FORCE_UPDATE="${FORCE_UPDATE:-true}"

echo "📋 배포 설정:"
echo "   - 네임스페이스: $NAMESPACE"
echo "   - 레지스트리: $REGISTRY"
echo "   - 이미지 태그: $IMAGE_TAG"
echo "   - 강제 업데이트: $FORCE_UPDATE"

# 1. 네임스페이스 확인 및 생성
echo "📦 네임스페이스 확인..."
if kubectl get namespace $NAMESPACE &>/dev/null; then
    echo "   - 네임스페이스 $NAMESPACE 이미 존재"
else
    echo "   - 네임스페이스 $NAMESPACE 생성 중..."
    kubectl create namespace $NAMESPACE
fi

# 3. Registry Secret 생성
echo "🔐 Registry Secret 생성..."
kubectl create secret docker-registry regcred \
    --docker-server=$REGISTRY \
    --docker-username=$REGISTRY_USER \
    --docker-password=$REGISTRY_PASS \
    -n $NAMESPACE

# 4. PV 생성 (k8s 폴더에 있으면)
if [ -f "k8s/pv.yaml" ]; then
    echo "📁 PV 생성..."
    kubectl apply -f k8s/pv.yaml
fi

# 5. 배포 (k8s 폴더 있으면 사용, 없으면 inline)
if [ -d "k8s" ] && [ -f "k8s/kustomization.yaml" ]; then
    echo "📤 Kustomize로 배포..."
    kubectl apply -k k8s/
else
    echo "📤 인라인 배포..."
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blacklist
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blacklist
  template:
    metadata:
      labels:
        app: blacklist
    spec:
      imagePullSecrets:
      - name: regcred
      initContainers:
      - name: init-permissions
        image: busybox:latest
        command: ['sh', '-c', 'mkdir -p /app/instance && chmod 777 /app/instance']
        volumeMounts:
        - name: instance-data
          mountPath: /app/instance
      containers:
      - name: blacklist
        image: $REGISTRY/blacklist:$IMAGE_TAG
        imagePullPolicy: Always
        ports:
        - containerPort: 2541
        env:
        - name: PORT
          value: "2541"
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: REGTECH_USERNAME
          value: "nextrade"
        - name: REGTECH_PASSWORD
          value: "Sprtmxm1@3"
        - name: SECUDIUM_USERNAME
          value: "nextrade"
        - name: SECUDIUM_PASSWORD
          value: "Sprtmxm1@3"
        volumeMounts:
        - name: instance-data
          mountPath: /app/instance
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
      volumes:
      - name: instance-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: blacklist
  namespace: $NAMESPACE
spec:
  type: NodePort
  selector:
    app: blacklist
  ports:
  - port: 2541
    targetPort: 2541
    nodePort: 32541
EOF
fi

# 6. 이미지 강제 업데이트 (CI/CD용)
if [ "$FORCE_UPDATE" = "true" ] && [ "$IMAGE_TAG" != "latest" ]; then
    echo "🔄 이미지 강제 업데이트..."
    
    # 배포가 완료된 후 이미지 태그 업데이트
    kubectl set image deployment/blacklist \
        blacklist=$REGISTRY/blacklist:$IMAGE_TAG \
        -n $NAMESPACE
    
    # 롤아웃 재시작 (동일 이미지여도 강제 재배포)
    kubectl rollout restart deployment/blacklist -n $NAMESPACE
    
    echo "✅ 이미지 업데이트 완료"
fi

# 7. 배포 대기
echo "⏳ Pod 시작 대기 중..."
kubectl wait --for=condition=ready pod -l app=blacklist -n $NAMESPACE --timeout=600s

# 8. 상태 확인
echo "📊 배포 상태:"
kubectl get all -n $NAMESPACE

# 9. 이미지 태그 확인
CURRENT_IMAGE=$(kubectl get deployment blacklist -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')
echo "🏷️  현재 이미지: $CURRENT_IMAGE"

# 10. 접속 정보
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
NODE_PORT=$(kubectl get svc blacklist -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "32541")

echo "
=====================================
✅ 배포 완료!
=====================================
🏷️  이미지: $CURRENT_IMAGE
🌐 접속 URL: http://$NODE_IP:$NODE_PORT
📊 대시보드: http://$NODE_IP:$NODE_PORT/
📚 API 문서: http://$NODE_IP:$NODE_PORT/docs
🔍 Health Check: http://$NODE_IP:$NODE_PORT/health
=====================================

유용한 명령어:
- Pod 로그: kubectl logs -f deployment/blacklist -n $NAMESPACE
- Pod 상태: kubectl get pods -n $NAMESPACE -w
- 배포 상태: kubectl rollout status deployment/blacklist -n $NAMESPACE
"