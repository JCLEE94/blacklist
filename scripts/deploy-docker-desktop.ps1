# Docker Desktop 환경용 통합 배포 스크립트

Write-Host "🐳 Docker Desktop 환경 감지 및 배포 시작..." -ForegroundColor Cyan

# 1. Docker Desktop 상태 확인
Write-Host "`n[1/7] Docker Desktop 상태 확인..." -ForegroundColor Yellow
$dockerStatus = docker info 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker Desktop이 실행되지 않았습니다. Docker Desktop을 시작하세요." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker Desktop 실행 중" -ForegroundColor Green

# 2. Kubernetes 활성화 확인
Write-Host "`n[2/7] Kubernetes 활성화 확인..." -ForegroundColor Yellow
$k8sStatus = kubectl version --short 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Kubernetes가 활성화되지 않았습니다." -ForegroundColor Red
    Write-Host "Docker Desktop 설정에서 Kubernetes를 활성화하세요." -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Kubernetes 활성화됨" -ForegroundColor Green

# 3. 기존 리소스 정리
Write-Host "`n[3/7] 기존 리소스 정리..." -ForegroundColor Yellow
kubectl delete namespace blacklist --force --grace-period=0 2>$null
Start-Sleep -Seconds 3

# 4. 네임스페이스 및 기본 리소스 생성
Write-Host "`n[4/7] 네임스페이스 및 리소스 생성..." -ForegroundColor Yellow
kubectl create namespace blacklist

# Registry Secret 생성
kubectl create secret docker-registry regcred `
    --docker-server=registry.jclee.me `
    --docker-username=qws9411 `
    --docker-password=bingogo1 `
    -n blacklist

# 5. Docker Desktop용 간단한 배포 (PVC 없이)
Write-Host "`n[5/7] Docker Desktop용 간단 배포..." -ForegroundColor Yellow

$deployment = @"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blacklist
  namespace: blacklist
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
      containers:
      - name: blacklist
        image: registry.jclee.me/blacklist:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 2541
        env:
        - name: PORT
          value: "2541"
        - name: PYTHONUNBUFFERED
          value: "1"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: blacklist
  namespace: blacklist
spec:
  type: LoadBalancer
  selector:
    app: blacklist
  ports:
  - port: 2541
    targetPort: 2541
    nodePort: 32541
"@

$deployment | kubectl apply -f -

# 6. 배포 대기 및 모니터링
Write-Host "`n[6/7] 배포 상태 모니터링..." -ForegroundColor Yellow

$maxAttempts = 60
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $podStatus = kubectl get pods -n blacklist -o jsonpath='{.items[0].status.phase}' 2>$null
    
    if ($podStatus -eq "Running") {
        Write-Host "✅ Pod 실행 중!" -ForegroundColor Green
        break
    }
    elseif ($podStatus -eq "Pending") {
        Write-Host "⏳ Pod 시작 중... ($attempt/60)" -ForegroundColor Gray
    }
    elseif ($podStatus -eq "Failed" -or $podStatus -eq "CrashLoopBackOff") {
        Write-Host "❌ Pod 실패!" -ForegroundColor Red
        kubectl describe pods -n blacklist
        exit 1
    }
    elseif ($podStatus -eq "ErrImagePull" -or $podStatus -eq "ImagePullBackOff") {
        Write-Host "❌ 이미지 Pull 실패!" -ForegroundColor Red
        Write-Host "로컬 이미지로 전환 시도..." -ForegroundColor Yellow
        
        # 로컬 이미지로 전환
        kubectl set image deployment/blacklist blacklist=blacklist:local -n blacklist
        kubectl patch deployment blacklist -n blacklist -p '{"spec":{"template":{"spec":{"containers":[{"name":"blacklist","imagePullPolicy":"Never"}]}}}}'
    }
    
    $attempt++
    Start-Sleep -Seconds 1
}

# 7. 최종 상태 확인
Write-Host "`n[7/7] 최종 상태 확인..." -ForegroundColor Yellow
kubectl get all -n blacklist

# 서비스 접속 정보
$service = kubectl get service blacklist -n blacklist -o json | ConvertFrom-Json
$nodePort = $service.spec.ports[0].nodePort

Write-Host "`n=====================================
✅ 배포 완료!
=====================================
접속 URL: http://localhost:$nodePort
대시보드: http://localhost:$nodePort/
API 문서: http://localhost:$nodePort/docs
=====================================`n" -ForegroundColor Green

# 로그 스트리밍 옵션
$showLogs = Read-Host "로그를 보시겠습니까? (y/n)"
if ($showLogs -eq 'y') {
    kubectl logs -f deployment/blacklist -n blacklist -c blacklist
}