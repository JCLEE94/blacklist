# Docker Desktop 환경용 통합 배포 스크립트 - 다중 환경 지원

Write-Host "🐳 Kubernetes 환경 감지 및 배포 시작..." -ForegroundColor Cyan

# 환경 변수 및 설정
$NAMESPACE = if ($env:NAMESPACE) { $env:NAMESPACE } else { "blacklist" }
$REGISTRY = if ($env:REGISTRY) { $env:REGISTRY } else { "registry.jclee.me" }
$REGISTRY_USER = if ($env:REGISTRY_USER) { $env:REGISTRY_USER } else { "qws9411" }
$REGISTRY_PASS = if ($env:REGISTRY_PASS) { $env:REGISTRY_PASS } else { "bingogo1" }
$IMAGE_TAG = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }
$NODE_PORT = if ($env:NODE_PORT) { $env:NODE_PORT } else { "32541" }
$DEPLOYMENT_TIMEOUT = if ($env:DEPLOYMENT_TIMEOUT) { $env:DEPLOYMENT_TIMEOUT } else { 300 }
$USE_LOCAL_IMAGE = if ($env:USE_LOCAL_IMAGE) { $env:USE_LOCAL_IMAGE } else { "false" }

# 프록시 설정 감지
if ($env:HTTP_PROXY -or $env:http_proxy) {
    $proxy = if ($env:HTTP_PROXY) { $env:HTTP_PROXY } else { $env:http_proxy }
    Write-Host "🔧 프록시 환경 감지: $proxy" -ForegroundColor Yellow
}

# 0. Kubernetes 종류 감지
Write-Host "`n[0/8] Kubernetes 환경 감지..." -ForegroundColor Yellow
$K8S_CONTEXT = kubectl config current-context 2>$null
$K8S_TYPE = "unknown"

if ($K8S_CONTEXT -like "*docker-desktop*") {
    $K8S_TYPE = "docker-desktop"
    Write-Host "📦 Docker Desktop Kubernetes 감지" -ForegroundColor Blue
} elseif ($K8S_CONTEXT -like "*minikube*") {
    $K8S_TYPE = "minikube"
    Write-Host "🔧 Minikube 감지" -ForegroundColor Blue
} elseif ($K8S_CONTEXT -like "*kind*") {
    $K8S_TYPE = "kind"
    Write-Host "🐋 Kind 클러스터 감지" -ForegroundColor Blue
} elseif ($K8S_CONTEXT -like "*k3s*" -or $K8S_CONTEXT -like "*k3d*") {
    $K8S_TYPE = "k3s"
    Write-Host "⚡ K3s/K3d 클러스터 감지" -ForegroundColor Blue
} elseif ($K8S_CONTEXT -like "*rancher*") {
    $K8S_TYPE = "rancher"
    Write-Host "🐄 Rancher Desktop 감지" -ForegroundColor Blue
} else {
    Write-Host "⚠️  알 수 없는 Kubernetes 환경: $K8S_CONTEXT" -ForegroundColor Yellow
    Write-Host "계속 진행합니다..." -ForegroundColor Cyan
}

# 1. Container Runtime 상태 확인
Write-Host "`n[1/8] Container Runtime 상태 확인..." -ForegroundColor Yellow
$CONTAINER_RUNTIME = "none"

if (Get-Command docker -ErrorAction SilentlyContinue) {
    $dockerStatus = docker info 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker 실행 중" -ForegroundColor Green
        $CONTAINER_RUNTIME = "docker"
    }
}

if ($CONTAINER_RUNTIME -eq "none" -and (Get-Command podman -ErrorAction SilentlyContinue)) {
    $podmanStatus = podman info 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Podman 실행 중" -ForegroundColor Green
        $CONTAINER_RUNTIME = "podman"
    }
}

if ($CONTAINER_RUNTIME -eq "none") {
    Write-Host "❌ Container Runtime이 실행되지 않았습니다." -ForegroundColor Red
    exit 1
}

# 2. Kubernetes 활성화 확인
Write-Host "`n[2/8] Kubernetes 활성화 확인..." -ForegroundColor Yellow
$k8sStatus = kubectl version --short 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Kubernetes가 활성화되지 않았습니다." -ForegroundColor Red
    
    # 환경별 안내
    switch ($K8S_TYPE) {
        "docker-desktop" {
            Write-Host "Docker Desktop 설정에서 Kubernetes를 활성화하세요." -ForegroundColor Yellow
        }
        "minikube" {
            Write-Host "minikube start 명령을 실행하세요." -ForegroundColor Yellow
        }
        "kind" {
            Write-Host "kind create cluster 명령을 실행하세요." -ForegroundColor Yellow
        }
        default {
            Write-Host "Kubernetes 클러스터를 시작하세요." -ForegroundColor Yellow
        }
    }
    exit 1
}
Write-Host "✅ Kubernetes 활성화됨" -ForegroundColor Green

# Storage Class 확인
Write-Host "`n[2.5/8] Storage Class 확인..." -ForegroundColor Yellow
$storageClasses = kubectl get storageclass -o json 2>$null | ConvertFrom-Json
$USE_HOSTPATH = $false
$STORAGE_CLASS = ""

if ($storageClasses.items.Count -eq 0) {
    Write-Host "⚠️  Storage Class가 없습니다. hostPath 사용" -ForegroundColor Yellow
    $USE_HOSTPATH = $true
} else {
    $defaultSC = $storageClasses.items | Where-Object { 
        $_.metadata.annotations."storageclass.kubernetes.io/is-default-class" -eq "true" 
    }
    if ($defaultSC) {
        $STORAGE_CLASS = $defaultSC.metadata.name
        Write-Host "✅ 기본 Storage Class: $STORAGE_CLASS" -ForegroundColor Green
    } else {
        $STORAGE_CLASS = $storageClasses.items[0].metadata.name
        Write-Host "⚠️  기본 Storage Class 없음. '$STORAGE_CLASS' 사용" -ForegroundColor Yellow
    }
}

# 3. 기존 리소스 정리
Write-Host "`n[3/8] 기존 리소스 정리..." -ForegroundColor Yellow

# 네임스페이스 상태 확인
$nsStatus = kubectl get namespace $NAMESPACE -o jsonpath='{.status.phase}' 2>$null
if ($nsStatus -eq "Terminating") {
    Write-Host "⚠️  네임스페이스가 Terminating 상태입니다. 강제 삭제 시도..." -ForegroundColor Yellow
    # Finalizers 제거
    kubectl patch namespace $NAMESPACE -p '{"metadata":{"finalizers":null}}' --type=merge 2>$null
    kubectl patch namespace $NAMESPACE -p '{"spec":{"finalizers":null}}' --type=merge 2>$null
}

# 일반 삭제
kubectl delete namespace $NAMESPACE --force --grace-period=0 2>$null

# 완전 삭제 대기
Write-Host "네임스페이스 삭제 대기 중..." -ForegroundColor Cyan
$deleted = $false
for ($i = 0; $i -lt 30; $i++) {
    $ns = kubectl get namespace $NAMESPACE 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✅ 네임스페이스 삭제 완료" -ForegroundColor Green
        $deleted = $true
        break
    }
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 1
}
Write-Host ""

# 4. 네임스페이스 및 기본 리소스 생성
Write-Host "`n[4/8] 네임스페이스 및 리소스 생성..." -ForegroundColor Yellow
kubectl create namespace $NAMESPACE

# Resource Quota 설정 (리소스 제한 환경용)
if ($K8S_TYPE -eq "docker-desktop" -or $K8S_TYPE -eq "minikube" -or $K8S_TYPE -eq "kind") {
    Write-Host "리소스 제한 설정 중..." -ForegroundColor Cyan
    @"
apiVersion: v1
kind: ResourceQuota
metadata:
  name: $NAMESPACE-quota
  namespace: $NAMESPACE
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.cpu: "4"
    limits.memory: 8Gi
    persistentvolumeclaims: "10"
"@ | kubectl apply -f -
}

# Registry Secret 생성
Write-Host "Registry Secret 생성 중..." -ForegroundColor Cyan
kubectl delete secret regcred -n $NAMESPACE 2>$null
kubectl create secret docker-registry regcred `
    --docker-server=$REGISTRY `
    --docker-username=$REGISTRY_USER `
    --docker-password=$REGISTRY_PASS `
    -n $NAMESPACE

# 5. 로컬 이미지 빌드 옵션
Write-Host "`n[5/8] 이미지 준비..." -ForegroundColor Yellow

$IMAGE_PULL_POLICY = "Always"
$IMAGE_NAME = "$REGISTRY/blacklist:$IMAGE_TAG"

if ($USE_LOCAL_IMAGE -eq "true" -or $K8S_TYPE -eq "minikube") {
    Write-Host "로컬 이미지 빌드 중..." -ForegroundColor Cyan
    
    # Minikube docker env 설정
    if ($K8S_TYPE -eq "minikube") {
        & minikube docker-env | Invoke-Expression
    }
    
    # 로컬 빌드
    if ((Test-Path "Dockerfile") -or (Test-Path "deployment/Dockerfile")) {
        $DOCKERFILE_PATH = if (Test-Path "deployment/Dockerfile") { "deployment/Dockerfile" } else { "Dockerfile" }
        
        & $CONTAINER_RUNTIME build -t blacklist:local -f $DOCKERFILE_PATH .
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ 로컬 이미지 빌드 완료" -ForegroundColor Green
            $IMAGE_PULL_POLICY = "Never"
            $IMAGE_NAME = "blacklist:local"
        }
    } else {
        Write-Host "⚠️  Dockerfile을 찾을 수 없습니다. Registry 이미지 사용" -ForegroundColor Yellow
    }
}

# 6. 배포 매니페스트 생성
Write-Host "`n[6/8] 배포 매니페스트 생성..." -ForegroundColor Yellow

# Service Type 결정
$SERVICE_TYPE = switch ($K8S_TYPE) {
    "kind" { "NodePort"; Write-Host "Kind 클러스터: NodePort 사용" -ForegroundColor Cyan; break }
    "minikube" { "NodePort"; Write-Host "Minikube: NodePort 사용" -ForegroundColor Cyan; break }
    default { "LoadBalancer" }
}

$deployment = @"
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
        image: $IMAGE_NAME
        imagePullPolicy: $IMAGE_PULL_POLICY
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
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
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
  type: $SERVICE_TYPE
  selector:
    app: blacklist
  ports:
  - port: 2541
    targetPort: 2541
    nodePort: $NODE_PORT
"@

$deployment | kubectl apply -f -

# 7. 배포 대기 및 모니터링
Write-Host "`n[7/8] 배포 상태 모니터링..." -ForegroundColor Yellow

$maxAttempts = [int]($DEPLOYMENT_TIMEOUT / 5)
$attempt = 0
$imagePullError = $false

while ($attempt -lt $maxAttempts) {
    # Pod 상태 체크
    $pods = kubectl get pods -n $NAMESPACE -l app=blacklist -o json 2>$null | ConvertFrom-Json
    
    if ($pods.items.Count -gt 0) {
        $pod = $pods.items[0]
        $podStatus = $pod.status.phase
        
        if ($pod.status.containerStatuses -and $pod.status.containerStatuses.Count -gt 0) {
            $containerState = $pod.status.containerStatuses[0].state
            $ready = $pod.status.containerStatuses[0].ready
            
            # Running 상태
            if ($containerState.running -and $ready) {
                Write-Host "✅ Pod 준비 완료!" -ForegroundColor Green
                break
            }
            
            # Waiting 상태
            if ($containerState.waiting) {
                $reason = $containerState.waiting.reason
                
                switch ($reason) {
                    { $_ -in "ErrImagePull", "ImagePullBackOff" } {
                        if (-not $imagePullError) {
                            Write-Host "`n❌ 이미지 Pull 실패: $($containerState.waiting.message)" -ForegroundColor Red
                            Write-Host "로컬 이미지로 전환 시도..." -ForegroundColor Yellow
                            
                            kubectl set image deployment/blacklist blacklist=blacklist:local -n $NAMESPACE
                            kubectl patch deployment blacklist -n $NAMESPACE -p '{"spec":{"template":{"spec":{"containers":[{"name":"blacklist","imagePullPolicy":"Never"}]}}}}'
                            $imagePullError = $true
                        }
                    }
                    "CrashLoopBackOff" {
                        Write-Host "`n❌ 컨테이너 충돌 반복!" -ForegroundColor Red
                        Write-Host "최근 로그:" -ForegroundColor Yellow
                        kubectl logs -n $NAMESPACE -l app=blacklist --tail=20
                        exit 1
                    }
                    default {
                        Write-Host -NoNewline "`r⏳ 대기 중: $reason ($attempt/$maxAttempts)"
                    }
                }
            }
            
            # Terminated 상태
            if ($containerState.terminated) {
                Write-Host "`n❌ 컨테이너 종료: $($containerState.terminated.reason) (Exit: $($containerState.terminated.exitCode))" -ForegroundColor Red
                kubectl logs -n $NAMESPACE -l app=blacklist --tail=50
                exit 1
            }
        }
        
        # Pending 상태 분석
        if ($podStatus -eq "Pending") {
            $events = kubectl get events -n $NAMESPACE --field-selector involvedObject.name=$($pod.metadata.name) -o json | ConvertFrom-Json
            if ($events.items | Where-Object { $_.reason -eq "FailedScheduling" }) {
                Write-Host "`n⚠️  스케줄링 문제 감지" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host -NoNewline "`r⏳ Pod 생성 대기 중... ($attempt/$maxAttempts)"
    }
    
    $attempt++
    Start-Sleep -Seconds 5
}

if ($attempt -ge $maxAttempts) {
    Write-Host "`n❌ 배포 시간 초과!" -ForegroundColor Red
    Write-Host "문제 진단:" -ForegroundColor Yellow
    kubectl describe deployment blacklist -n $NAMESPACE
    kubectl describe pods -n $NAMESPACE -l app=blacklist
    exit 1
}

# 8. 최종 상태 확인 및 접속 정보
Write-Host "`n[8/8] 최종 상태 확인..." -ForegroundColor Yellow
kubectl get all -n $NAMESPACE

# 서비스 접속 정보
$service = kubectl get service blacklist -n $NAMESPACE -o json | ConvertFrom-Json
$nodePort = $service.spec.ports[0].nodePort

# 환경별 접속 URL 안내
$ACCESS_URL = switch ($K8S_TYPE) {
    "minikube" {
        $minikubeIp = minikube ip
        "http://${minikubeIp}:$nodePort"
        Write-Host "`nMinikube 터널링이 필요할 수 있습니다:" -ForegroundColor Yellow
        Write-Host "minikube service blacklist -n $NAMESPACE" -ForegroundColor Cyan
    }
    "kind" {
        "http://localhost:$nodePort"
        Write-Host "`nKind 포트 포워딩이 필요할 수 있습니다:" -ForegroundColor Yellow
        Write-Host "kubectl port-forward -n $NAMESPACE service/blacklist ${nodePort}:2541" -ForegroundColor Cyan
    }
    default {
        "http://localhost:$nodePort"
    }
}

Write-Host "`n=====================================
✅ 배포 완료!
=====================================
🌍 Kubernetes: $K8S_TYPE
📦 Container Runtime: $CONTAINER_RUNTIME
🔗 접속 URL: $ACCESS_URL
📊 대시보드: $ACCESS_URL/
📚 API 문서: $ACCESS_URL/docs
=====================================

유용한 명령어:
- Pod 로그: kubectl logs -f deployment/blacklist -n $NAMESPACE
- Pod 상태: kubectl get pods -n $NAMESPACE -w
- 서비스 확인: kubectl get svc -n $NAMESPACE
- 이벤트 확인: kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'
=====================================`n" -ForegroundColor Green

# 자동 초기 수집 확인
Write-Host "🔄 자동 초기 수집 상태 확인 중..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
try {
    $collectionStatus = Invoke-RestMethod -Uri "$ACCESS_URL/api/collection/status" -Method Get
    Write-Host "✅ 수집 서비스 정상 작동" -ForegroundColor Green
    $collectionStatus | ConvertTo-Json -Depth 10
} catch {
    Write-Host "⚠️  수집 서비스 확인 불가 (네트워크 설정 확인 필요)" -ForegroundColor Yellow
}

# 로그 스트리밍 옵션
if ([Environment]::UserInteractive) {
    $showLogs = Read-Host "로그를 보시겠습니까? (y/n)"
    if ($showLogs -eq 'y') {
        kubectl logs -f deployment/blacklist -n $NAMESPACE -c blacklist
    }
}