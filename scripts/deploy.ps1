# Windows 배포 스크립트

Write-Host "🚀 Windows 환경 Blacklist 배포 시작..." -ForegroundColor Cyan

# 기본 설정
$NAMESPACE = "blacklist"
$REGISTRY = "registry.jclee.me"
$REGISTRY_USER = "qws9411"
$REGISTRY_PASS = "bingogo1"

# 1. 기존 네임스페이스 삭제
Write-Host "🗑️  기존 리소스 정리..." -ForegroundColor Yellow
kubectl delete namespace $NAMESPACE --force --grace-period=0 2>$null

# Terminating 상태 해결
kubectl patch namespace $NAMESPACE -p '{"metadata":{"finalizers":null}}' --type=merge 2>$null

# 대기
Start-Sleep -Seconds 5

# 2. 네임스페이스 생성
Write-Host "📦 네임스페이스 생성..." -ForegroundColor Green
kubectl create namespace $NAMESPACE

# 3. Registry Secret 생성
Write-Host "🔐 Registry Secret 생성..." -ForegroundColor Green
kubectl create secret docker-registry regcred `
    --docker-server=$REGISTRY `
    --docker-username=$REGISTRY_USER `
    --docker-password=$REGISTRY_PASS `
    -n $NAMESPACE

# 4. PV 생성 (k8s 폴더에 있으면)
if (Test-Path "k8s/pv.yaml") {
    Write-Host "📁 PV 생성..." -ForegroundColor Green
    kubectl apply -f k8s/pv.yaml
}

# 5. 배포 (k8s 폴더 있으면 사용, 없으면 inline)
if ((Test-Path "k8s") -and (Test-Path "k8s/kustomization.yaml")) {
    Write-Host "📤 Kustomize로 배포..." -ForegroundColor Green
    kubectl apply -k k8s/
} else {
    Write-Host "📤 인라인 배포..." -ForegroundColor Green
    @"
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
        image: $REGISTRY/blacklist:latest
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
"@ | kubectl apply -f -
}

# 6. 배포 대기
Write-Host "⏳ Pod 시작 대기 중..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=blacklist -n $NAMESPACE --timeout=300s

# 7. 상태 확인
Write-Host "📊 배포 상태:" -ForegroundColor Cyan
kubectl get all -n $NAMESPACE

# 8. 접속 정보
$NODE_IP = kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'
Write-Host "
=====================================
✅ 배포 완료!
=====================================
접속 URL: http://${NODE_IP}:32541
대시보드: http://${NODE_IP}:32541/
API 문서: http://${NODE_IP}:32541/docs
=====================================

Pod 로그 확인:
kubectl logs -f deployment/blacklist -n $NAMESPACE
" -ForegroundColor Green