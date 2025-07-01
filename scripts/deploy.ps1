# Windows 배포 스크립트

# 기존 리소스 정리
kubectl delete all --all -n blacklist 2>$null
kubectl create namespace blacklist 2>$null

# Registry Secret 생성 (미리 설정된 환경변수 사용)
kubectl delete secret regcred -n blacklist 2>$null
kubectl create secret docker-registry regcred `
  --docker-server=registry.jclee.me `
  --docker-username=registry_ `
  --docker-password=registry_ `
  -n blacklist

# 배포
kubectl apply -k k8s/

Start-Sleep -Seconds 5
kubectl get all -n blacklist