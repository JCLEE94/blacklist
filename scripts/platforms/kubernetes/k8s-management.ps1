# Blacklist Kubernetes 관리 스크립트 (PowerShell)
# 작성자: Claude
# 설명: Kubernetes 배포 관리를 위한 통합 스크립트

param(
    [Parameter(Position=0)]
    [string]$Command,
    
    [Parameter()]
    [string]$Tag = "latest",
    
    [Parameter()]
    [int]$Replicas = 3,
    
    [Parameter()]
    [string]$Pod = "",
    
    [Parameter()]
    [switch]$Help
)

# 설정
$Namespace = "blacklist"
$AppName = "blacklist"
$Registry = "registry.jclee.me"
$Image = "${Registry}/${AppName}"
$KustomizeDir = "./k8s"

# 색상 함수
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

# 사용법 출력
function Show-Usage {
    Write-Host @"
사용법: .\k8s-management.ps1 [명령] [옵션]

명령:
  init          - 초기 배포 (네임스페이스, 시크릿, 볼륨 생성)
  deploy        - 애플리케이션 배포/업데이트
  restart       - 디플로이먼트 재시작
  rollback      - 이전 버전으로 롤백
  status        - 배포 상태 확인
  logs          - 로그 확인
  scale         - 파드 스케일 조정
  delete        - 모든 리소스 삭제
  port-forward  - 로컬 포트 포워딩
  exec          - 파드에 명령 실행
  describe      - 리소스 상세 정보
  events        - 이벤트 확인
  dashboard     - Kubernetes 대시보드 열기

옵션:
  -Tag          - 이미지 태그 (기본값: latest)
  -Replicas     - 레플리카 수 (scale 명령용)
  -Pod          - 파드 이름 (logs, exec 명령용)

예제:
  .\k8s-management.ps1 init
  .\k8s-management.ps1 deploy -Tag v1.2.3
  .\k8s-management.ps1 scale -Replicas 5
  .\k8s-management.ps1 logs -Pod blacklist-xyz
"@
}

# 네임스페이스 확인 및 생성
function Ensure-Namespace {
    $namespaceExists = kubectl get namespace $Namespace 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Info "네임스페이스 '$Namespace' 생성 중..."
        kubectl create namespace $Namespace
        Write-Success "네임스페이스 생성 완료"
    } else {
        Write-Info "네임스페이스 '$Namespace' 이미 존재"
    }
}

# 초기 배포
function Initialize-Deployment {
    Write-Info "초기 배포 시작..."
    
    # 네임스페이스 생성
    Ensure-Namespace
    
    # Docker 레지스트리 시크릿 확인
    $secretExists = kubectl get secret regcred -n $Namespace 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Docker 레지스트리 시크릿 생성 중..."
        $dockerUser = Read-Host "Docker 사용자명"
        $dockerPass = Read-Host "Docker 비밀번호" -AsSecureString
        $dockerPassText = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($dockerPass))
        
        kubectl create secret docker-registry regcred `
            --docker-server=$Registry `
            --docker-username=$dockerUser `
            --docker-password=$dockerPassText `
            -n $Namespace
        
        Write-Success "Docker 레지스트리 시크릿 생성 완료"
    }
    
    # Kustomize로 배포
    Write-Info "Kustomize로 리소스 배포 중..."
    kubectl apply -k $KustomizeDir
    
    # 배포 대기
    Write-Info "배포 완료 대기 중..."
    kubectl rollout status deployment/$AppName -n $Namespace --timeout=300s
    
    Write-Success "초기 배포 완료!"
}

# 애플리케이션 배포/업데이트
function Deploy-Application {
    Write-Info "애플리케이션 배포 시작 (태그: $Tag)..."
    
    # 이미지 태그 업데이트 (kustomize가 있는 경우)
    if (Get-Command kustomize -ErrorAction SilentlyContinue) {
        Push-Location $KustomizeDir
        kustomize edit set image "${Image}:${Tag}"
        Pop-Location
    }
    
    # 배포
    kubectl apply -k $KustomizeDir
    
    # 롤아웃 대기
    Write-Info "롤아웃 대기 중..."
    kubectl rollout status deployment/$AppName -n $Namespace --timeout=300s
    
    Write-Success "배포 완료!"
}

# 디플로이먼트 재시작
function Restart-Deployment {
    Write-Info "디플로이먼트 재시작 중..."
    kubectl rollout restart deployment/$AppName -n $Namespace
    
    Write-Info "재시작 완료 대기 중..."
    kubectl rollout status deployment/$AppName -n $Namespace --timeout=300s
    
    Write-Success "재시작 완료!"
}

# 롤백
function Rollback-Deployment {
    Write-Info "이전 버전으로 롤백 중..."
    kubectl rollout undo deployment/$AppName -n $Namespace
    
    Write-Info "롤백 완료 대기 중..."
    kubectl rollout status deployment/$AppName -n $Namespace --timeout=300s
    
    Write-Success "롤백 완료!"
}

# 상태 확인
function Get-DeploymentStatus {
    Write-Info "배포 상태 확인..."
    Write-Host ""
    
    Write-Host "=== 디플로이먼트 ===" -ForegroundColor Cyan
    kubectl get deployments -n $Namespace
    Write-Host ""
    
    Write-Host "=== 파드 ===" -ForegroundColor Cyan
    kubectl get pods -n $Namespace -o wide
    Write-Host ""
    
    Write-Host "=== 서비스 ===" -ForegroundColor Cyan
    kubectl get services -n $Namespace
    Write-Host ""
    
    Write-Host "=== 인그레스 ===" -ForegroundColor Cyan
    kubectl get ingress -n $Namespace
    Write-Host ""
    
    Write-Host "=== HPA ===" -ForegroundColor Cyan
    kubectl get hpa -n $Namespace
}

# 로그 확인
function Get-PodLogs {
    if ([string]::IsNullOrEmpty($Pod)) {
        # 첫 번째 파드 선택
        $Pod = kubectl get pods -n $Namespace -l app=$AppName -o jsonpath='{.items[0].metadata.name}'
    }
    
    if ([string]::IsNullOrEmpty($Pod)) {
        Write-Error "실행 중인 파드를 찾을 수 없습니다"
        exit 1
    }
    
    Write-Info "파드 '$Pod'의 로그 확인..."
    kubectl logs -f $Pod -n $Namespace
}

# 스케일 조정
function Set-DeploymentScale {
    Write-Info "레플리카 수를 $Replicas로 조정 중..."
    kubectl scale deployment/$AppName -n $Namespace --replicas=$Replicas
    
    Write-Info "스케일 조정 완료 대기 중..."
    kubectl rollout status deployment/$AppName -n $Namespace --timeout=300s
    
    Write-Success "스케일 조정 완료!"
}

# 모든 리소스 삭제
function Remove-AllResources {
    Write-Warning "모든 리소스를 삭제합니다. 계속하시겠습니까? (y/N)"
    $confirm = Read-Host
    
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Info "삭제 취소됨"
        exit 0
    }
    
    Write-Info "모든 리소스 삭제 중..."
    kubectl delete -k $KustomizeDir
    
    Write-Success "삭제 완료!"
}

# 포트 포워딩
function Start-PortForward {
    $podName = kubectl get pods -n $Namespace -l app=$AppName -o jsonpath='{.items[0].metadata.name}'
    
    if ([string]::IsNullOrEmpty($podName)) {
        Write-Error "실행 중인 파드를 찾을 수 없습니다"
        exit 1
    }
    
    Write-Info "포트 포워딩 설정 (로컬 8541 -> 파드 2541)..."
    kubectl port-forward $podName 8541:2541 -n $Namespace
}

# 파드에 명령 실행
function Invoke-PodExec {
    if ([string]::IsNullOrEmpty($Pod)) {
        $Pod = kubectl get pods -n $Namespace -l app=$AppName -o jsonpath='{.items[0].metadata.name}'
    }
    
    if ([string]::IsNullOrEmpty($Pod)) {
        Write-Error "실행 중인 파드를 찾을 수 없습니다"
        exit 1
    }
    
    Write-Info "파드 '$Pod'에 접속 중..."
    kubectl exec -it $Pod -n $Namespace -- /bin/bash
}

# 리소스 상세 정보
function Get-ResourceDetails {
    Write-Info "리소스 상세 정보..."
    
    Write-Host "=== 디플로이먼트 ===" -ForegroundColor Cyan
    kubectl describe deployment/$AppName -n $Namespace
    
    Write-Host "`n=== 최신 파드 ===" -ForegroundColor Cyan
    $podName = kubectl get pods -n $Namespace -l app=$AppName -o jsonpath='{.items[0].metadata.name}'
    if (-not [string]::IsNullOrEmpty($podName)) {
        kubectl describe pod/$podName -n $Namespace
    }
}

# 이벤트 확인
function Get-NamespaceEvents {
    Write-Info "최근 이벤트 확인..."
    kubectl get events -n $Namespace --sort-by='.lastTimestamp' | Select-Object -Last 20
}

# Kubernetes 대시보드 열기
function Open-Dashboard {
    Write-Info "Kubernetes 대시보드 프록시 시작..."
    Write-Warning "브라우저에서 http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/ 접속"
    kubectl proxy
}

# 메인 실행
if ($Help) {
    Show-Usage
    exit 0
}

switch ($Command) {
    "init" { Initialize-Deployment }
    "deploy" { Deploy-Application }
    "restart" { Restart-Deployment }
    "rollback" { Rollback-Deployment }
    "status" { Get-DeploymentStatus }
    "logs" { Get-PodLogs }
    "scale" { Set-DeploymentScale }
    "delete" { Remove-AllResources }
    "port-forward" { Start-PortForward }
    "exec" { Invoke-PodExec }
    "describe" { Get-ResourceDetails }
    "events" { Get-NamespaceEvents }
    "dashboard" { Open-Dashboard }
    default { 
        if ([string]::IsNullOrEmpty($Command)) {
            Write-Error "명령이 지정되지 않았습니다"
        } else {
            Write-Error "알 수 없는 명령: $Command"
        }
        Show-Usage
        exit 1
    }
}