# 로컬 이미지를 사용한 배포 스크립트 (ImagePullBackOff 회피)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Blacklist 로컬 배포" -ForegroundColor Cyan
Write-Host "  (Private Registry 없이)" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. 로컬 이미지 빌드
Write-Host "[1/4] 로컬 Docker 이미지 빌드..." -ForegroundColor Yellow
if (Test-Path "deployment/Dockerfile") {
    docker build -f deployment/Dockerfile -t blacklist:local .
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] 이미지 빌드 성공" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] 이미지 빌드 실패" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[WARNING] Dockerfile을 찾을 수 없습니다." -ForegroundColor Yellow
    Write-Host "기본 nginx 이미지를 사용합니다." -ForegroundColor Yellow
    $useNginx = $true
}
Write-Host ""

# 2. deployment.yaml 수정
Write-Host "[2/4] Deployment 설정 수정..." -ForegroundColor Yellow

# 임시 deployment 파일 생성
$tempDeployment = @"
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
      containers:
      - name: blacklist
        image: $(if ($useNginx) { "nginx:latest" } else { "blacklist:local" })
        imagePullPolicy: $(if ($useNginx) { "IfNotPresent" } else { "Never" })
        ports:
        - containerPort: $(if ($useNginx) { "80" } else { "2541" })
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "256Mi"
            cpu: "250m"
"@

$tempDeployment | Out-File -FilePath "k8s/deployment-local.yaml" -Encoding UTF8
Write-Host "[OK] 로컬 deployment 파일 생성" -ForegroundColor Green
Write-Host ""

# 3. 배포
Write-Host "[3/4] Kubernetes 배포..." -ForegroundColor Yellow

# 네임스페이스
kubectl apply -f k8s/namespace.yaml

# ConfigMap과 Secret (있는 경우)
if (Test-Path "k8s/configmap.yaml") {
    kubectl apply -f k8s/configmap.yaml
}
if (Test-Path "k8s/secret.yaml") {
    kubectl apply -f k8s/secret.yaml
}

# 로컬 deployment 적용
kubectl apply -f k8s/deployment-local.yaml

# 서비스
kubectl apply -f k8s/service.yaml

Write-Host "[OK] 배포 완료" -ForegroundColor Green
Write-Host ""

# 4. 상태 확인
Write-Host "[4/4] Pod 상태 확인..." -ForegroundColor Yellow
kubectl get pods -n blacklist
Write-Host ""

# 포트 포워딩 안내
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  접속 방법" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "포트 포워딩 실행:" -ForegroundColor Yellow
Write-Host "kubectl port-forward -n blacklist deployment/blacklist 8080:$(if ($useNginx) { "80" } else { "2541" })" -ForegroundColor Gray
Write-Host ""
Write-Host "브라우저에서 접속:" -ForegroundColor Yellow
Write-Host "http://localhost:8080" -ForegroundColor Gray
Write-Host ""

# 정리
if (Test-Path "k8s/deployment-local.yaml") {
    Remove-Item "k8s/deployment-local.yaml"
}

Read-Host "Press Enter to exit"