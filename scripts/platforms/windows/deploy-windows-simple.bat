@echo off
REM 간단한 Blacklist 배포 스크립트 (ArgoCD 제외)

echo Blacklist 배포 시작...
echo.

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

echo.
echo Pending Pod 삭제...
kubectl delete pods -n blacklist --field-selector=status.phase=Pending 2>nul

echo.
echo === 현재 상태 ===
kubectl get pods -n blacklist

echo.
echo 완료!
pause