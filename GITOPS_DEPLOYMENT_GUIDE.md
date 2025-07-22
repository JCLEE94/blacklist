# GitOps 완전 배포 가이드

## 🎯 개요

완전히 재구성된 GitOps CI/CD 파이프라인으로 blacklist 애플리케이션을 자동 배포합니다.

### 🏗️ 아키텍처
```
GitHub → GitOps Pipeline → Docker Registry → Helm Chart → ArgoCD → Kubernetes
```

## 📋 사전 준비사항

### 1. GitHub Secrets 설정

**필수 Secrets** (GitHub Repository Settings → Secrets and variables → Actions):
```bash
DOCKER_REGISTRY_USER=admin
DOCKER_REGISTRY_PASS=bingogo1
HELM_REPO_USERNAME=admin
HELM_REPO_PASSWORD=bingogo1
```

**자동 설정 방법**:
```bash
chmod +x setup-github-secrets.sh
./setup-github-secrets.sh
```

### 2. 외부 서비스 정보

- **Docker Registry**: https://registry.jclee.me (admin/bingogo1)
- **Helm Repository**: https://charts.jclee.me (admin/bingogo1)
- **ArgoCD Server**: https://argo.jclee.me (admin/bingogo1)

## 🚀 배포 실행 방법

### 방법 1: 자동 GitOps 배포 (권장)

```bash
# 1. GitHub Secrets 설정 (한 번만)
./setup-github-secrets.sh

# 2. Registry 인증 준비
./fix-registry-auth.sh

# 3. 변경사항 커밋 및 푸시
git add .
git commit -m "feat: Complete GitOps pipeline deployment"
git push origin main

# 4. GitHub Actions에서 자동 실행됨
# - 코드 품질 검사
# - Docker 이미지 빌드 및 푸시
# - Helm 차트 패키징 및 업로드
# - ArgoCD 배포 및 검증
```

### 방법 2: 수동 배포 테스트

```bash
# 완전한 배포 검증 실행
chmod +x complete-deployment-test.sh
./complete-deployment-test.sh
```

## 📊 GitOps 파이프라인 단계

### 1. **Quality & Security** 
- 코드 품질 검사 (flake8, black, isort)
- 보안 스캔 (bandit, safety)
- 테스트 실행 (pytest)

### 2. **Build & Push Docker Image**
- Multi-tag 전략:
  - `latest`
  - `sha-{commit_hash}`
  - `date-{timestamp}`
  - `stable` (main 브랜치)
  - `dev` (develop 브랜치)

### 3. **Package & Push Helm Chart**
- Helm 차트 버전 자동 업데이트
- ChartMuseum에 업로드
- 차트 업로드 검증

### 4. **Update K8s Manifests**
- 이미지 태그 자동 업데이트
- Registry Secret 생성
- Kubernetes 매니페스트 적용

### 5. **ArgoCD Deploy & Verify**
- ArgoCD Application 생성/업데이트
- 자동 동기화 대기
- 배포 상태 검증

### 6. **Final Verification**
- 서비스 헬스체크
- API 엔드포인트 테스트
- 성능 테스트
- 최종 상태 확인

### 7. **Notification**
- 배포 성공/실패 알림
- 접속 정보 제공

## 🔧 주요 구성 파일

### 워크플로우
- `.github/workflows/gitops-pipeline.yml` - 메인 GitOps 파이프라인

### Helm Chart
- `helm/blacklist/` - 완전한 Helm 차트 구조
- `helm/blacklist/values.yaml` - 기본 설정
- `helm/blacklist/values-prod.yaml` - 프로덕션 설정

### ArgoCD
- `k8s-gitops/argocd/blacklist-app-chartrepo.yaml` - ArgoCD Application 정의

### 스크립트
- `setup-github-secrets.sh` - GitHub Secrets 자동 설정
- `fix-registry-auth.sh` - Registry 인증 문제 해결
- `complete-deployment-test.sh` - 완전한 배포 검증

## 🎯 배포 후 접속 정보

배포 완료 후 다음 URL로 접속 가능:

```bash
# Node IP 확인
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}')

# 서비스 URL들
echo "애플리케이션: http://$NODE_IP:32452"
echo "Health Check: http://$NODE_IP:32452/health"
echo "API Stats: http://$NODE_IP:32452/api/stats"
echo "Test Endpoint: http://$NODE_IP:32452/test"
echo "ArgoCD Dashboard: https://argo.jclee.me"
```

## 🔍 모니터링 명령어

### 배포 상태 확인
```bash
# Pod 상태
kubectl get pods -n blacklist

# ArgoCD Application 상태
kubectl get application blacklist -n argocd

# 서비스 상태
kubectl get svc -n blacklist

# 전체 리소스
kubectl get all -n blacklist
```

### 로그 확인
```bash
# 애플리케이션 로그
kubectl logs -f deployment/blacklist -n blacklist

# ArgoCD 로그
kubectl logs -f deployment/argocd-application-controller -n argocd

# 이벤트 확인
kubectl get events -n blacklist --sort-by='.lastTimestamp'
```

### 성능 모니터링
```bash
# 리소스 사용량
kubectl top pods -n blacklist
kubectl top nodes

# HPA 상태 (설정된 경우)
kubectl get hpa -n blacklist
```

## 🛠️ 트러블슈팅

### 일반적인 문제들

#### 1. ImagePullBackOff 오류
```bash
# Registry Secret 재생성
./fix-registry-auth.sh

# Pod 재시작
kubectl delete pods -l app=blacklist -n blacklist
```

#### 2. ArgoCD Sync 실패
```bash
# 수동 동기화
kubectl patch application blacklist -n argocd --type merge -p '{"operation":{"sync":{"prune":true}}}'

# Application 재생성
kubectl delete application blacklist -n argocd
kubectl apply -f k8s-gitops/argocd/blacklist-app-chartrepo.yaml
```

#### 3. 서비스 접근 불가
```bash
# 서비스 및 엔드포인트 확인
kubectl get svc,endpoints -n blacklist

# NodePort 상태 확인
kubectl get svc blacklist -n blacklist -o yaml
```

#### 4. GitHub Actions 실패
- GitHub Secrets 설정 확인
- Self-hosted runner 상태 확인
- 외부 서비스 접근성 확인

### 로그 수집
```bash
# 전체 진단 정보 수집
kubectl describe pods -n blacklist > debug-pods.log
kubectl get events -n blacklist --sort-by='.lastTimestamp' > debug-events.log
kubectl get application blacklist -n argocd -o yaml > debug-argocd.log
```

## 📈 성능 최적화

### 스케일링
```bash
# 수동 스케일링
kubectl scale deployment blacklist --replicas=5 -n blacklist

# HPA 확인 (자동 스케일링)
kubectl get hpa -n blacklist
```

### 리소스 조정
Helm values.yaml에서 리소스 설정 조정:
```yaml
resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 1Gi
```

## 🔄 GitOps 워크플로우 특징

### 완전 자동화
- 코드 푸시 → 자동 빌드 → 자동 배포 → 자동 검증
- Self-healing: ArgoCD가 수동 변경사항을 자동 복구
- Image Updater: 새 이미지 자동 감지 및 배포

### 보안 강화
- GitHub Secrets로 인증 정보 관리
- Private registry 및 chart repository 사용
- RBAC 기반 ArgoCD 접근 제어

### 멀티 환경 지원
- Development: `develop` 브랜치 → `dev` 태그
- Production: `main` 브랜치 → `stable` 태그
- Feature: Feature 브랜치별 독립 배포 가능

## ✅ 완료 체크리스트

배포 완료를 위한 체크리스트:

- [ ] GitHub Secrets 설정 완료
- [ ] Registry 인증 Secret 생성
- [ ] ArgoCD Application 배포
- [ ] Pod Running 상태 확인
- [ ] 서비스 접근성 테스트
- [ ] API 엔드포인트 테스트
- [ ] 성능 테스트 통과
- [ ] ArgoCD Sync 상태 확인
- [ ] 모니터링 설정 완료

모든 항목이 완료되면 GitOps 배포가 성공적으로 완료된 것입니다! 🎉