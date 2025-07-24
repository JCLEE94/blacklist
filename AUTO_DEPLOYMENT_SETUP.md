# 자동 배포 설정 완료

## 구성 요소

### 1. GitHub Actions Workflow
- **파일**: `.github/workflows/auto-deploy.yaml`
- **기능**: 
  - main 브랜치 푸시 시 자동 빌드
  - Docker 이미지 빌드 및 레지스트리 푸시
  - 멀티 태그 전략 (latest, sha-hash, date)

### 2. ArgoCD 설정
- **파일**: `argocd-auto-deploy.yaml`
- **기능**:
  - 자동 동기화 활성화 (automated.prune=true, selfHeal=true)
  - Helm 차트 자동 업데이트 (targetRevision: "*")
  - 재시도 정책 설정 (5회, exponential backoff)

### 3. ArgoCD Image Updater
- **상태**: 설치 및 구성 완료
- **기능**:
  - 2분마다 새 이미지 확인
  - 자동으로 최신 이미지로 업데이트
  - Registry 인증 설정 완료

### 4. RBAC 권한
- **파일**: `argocd-image-updater-rbac.yaml`
- **기능**: Image Updater가 blacklist namespace의 secret 읽기 권한

## 현재 상태

### ✅ 완료된 항목
1. GitHub Actions 워크플로우 생성
2. ArgoCD 자동 동기화 설정
3. ArgoCD Image Updater 설치 및 구성
4. RBAC 권한 설정
5. 모니터링 스크립트 생성
6. 간편 배포 스크립트 (`deploy.sh`)

### ⚠️ 추가 설정 필요
1. **Docker Registry 인증**
   - GitHub Actions에서 이미지 푸시를 위한 인증 필요
   - `scripts/setup-registry-auth.sh` 실행하여 설정
   
2. **GitHub Secrets 설정**
   - DOCKER_REGISTRY_URL
   - DOCKER_REGISTRY_USER
   - DOCKER_REGISTRY_PASS

## 사용 방법

### 자동 배포
```bash
# 코드 변경 후
git add .
git commit -m "feat: 새 기능 추가"
git push origin main

# 또는 간편 스크립트 사용
./deploy.sh
```

### 수동 배포
```bash
# Docker 이미지 빌드 및 푸시 (인증 필요)
docker build -f deployment/Dockerfile -t registry.jclee.me/jclee94/blacklist:latest .
docker push registry.jclee.me/jclee94/blacklist:latest

# ArgoCD 동기화
argocd app sync blacklist --grpc-web
```

### 모니터링
```bash
# 배포 진행 상황 모니터링
./monitor-auto-deploy.sh

# ArgoCD 상태 확인
kubectl get app blacklist -n argocd

# Pod 상태 확인
kubectl get pods -n blacklist -w

# 버전 확인
curl http://192.168.50.110:32542/health | jq '.details.version'
```

## 롤백

### 자동 롤백
ArgoCD의 self-heal 기능으로 문제 발생 시 자동 롤백

### 수동 롤백
```bash
# ArgoCD를 통한 롤백
argocd app rollback blacklist --grpc-web

# Kubernetes 직접 롤백
kubectl rollout undo deployment/blacklist -n blacklist
```

## 주의사항

1. **데이터 보존**: PVC를 사용하므로 데이터는 배포 시에도 보존됨
2. **수동 동기화 복원**: 필요 시 자동 동기화 비활성화 가능
   ```bash
   kubectl patch app blacklist -n argocd --type='json' \
     -p='[{"op": "remove", "path": "/spec/syncPolicy/automated"}]'
   ```
3. **이미지 업데이트**: ArgoCD Image Updater가 2분마다 확인

## 트러블슈팅

### Docker Registry 인증 실패
```bash
# Registry 인증 설정
./scripts/setup-registry-auth.sh

# Secret 확인
kubectl get secret regcred -n blacklist
kubectl get secret regcred -n argocd
```

### Image Updater 오류
```bash
# 로그 확인
kubectl logs -n argocd deployment/argocd-image-updater

# 재시작
kubectl rollout restart deployment argocd-image-updater -n argocd
```

### GitHub Actions 실패
1. GitHub Secrets 설정 확인
2. self-hosted runner 상태 확인
3. Docker buildx 설정 확인