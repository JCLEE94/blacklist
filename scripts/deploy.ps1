# Windows 배포 스크립트

# Registry 로그인
Write-Host "Registry 로그인..." -ForegroundColor Yellow
docker login registry.jclee.me

# 기존 리소스 정리
kubectl delete all --all -n blacklist 2>$null
kubectl create namespace blacklist 2>$null

# Registry Secret 생성
kubectl delete secret regcred -n blacklist 2>$null
kubectl create secret docker-registry regcred `
  --docker-server=registry.jclee.me `
  --docker-username=$env:DOCKER_USERNAME `
  --docker-password=$env:DOCKER_PASSWORD `
  -n blacklist

# 배포
kubectl apply -k k8s/

Start-Sleep -Seconds 5
kubectl get all -n blacklist