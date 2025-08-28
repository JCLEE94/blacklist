# ArgoCD 자동 동기화 설정 가이드

## 1. ArgoCD 토큰 생성

```bash
# ArgoCD CLI로 로그인
argocd login argo.jclee.me --grpc-web

# 토큰 생성 (CI/CD용)
argocd account generate-token --account admin --grpc-web
```

## 2. GitHub Secrets 설정

GitHub 저장소에서 다음 Secret을 추가:
- Settings → Secrets and variables → Actions
- New repository secret
- Name: `ARGOCD_TOKEN`
- Value: 위에서 생성한 토큰

## 3. CI/CD 파이프라인 동작

파이프라인이 실행되면:
1. Docker 이미지 빌드 및 푸시
2. ArgoCD 자동 동기화 트리거
3. 배포 상태 모니터링

## 4. 수동 동기화 (필요시)

```bash
# ArgoCD CLI
argocd app sync blacklist --grpc-web

# kubectl (직접 적용)
kubectl apply -k k8s/

# 상태 확인
argocd app get blacklist --grpc-web
kubectl get pods -n blacklist
```

## 5. 문제 해결

### ConfigMap not found 오류
```bash
# ConfigMap 확인
kubectl get configmap -n blacklist

# 수동 생성
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/blacklist-secrets.yaml
kubectl apply -f k8s/blacklist-credentials.yaml
```

### ArgoCD 동기화 실패
```bash
# ArgoCD 앱 새로고침
argocd app refresh blacklist --grpc-web

# 강제 동기화
argocd app sync blacklist --force --grpc-web

# 로그 확인
argocd app logs blacklist --grpc-web
```