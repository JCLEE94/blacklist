# 🚀 블랙리스트 관리 시스템 GitOps 배포 체크리스트

## 📋 배포 준비 상태 점검 (v1.0.20)

### ✅ 1. K8s 매니페스트 업데이트 완료
- [x] **k8s/overlays/production/kustomization.yaml**
  - 이미지 태그: `latest` → `1.0.20` ✅
  - 버전 레이블: `1.0.17` → `1.0.20` ✅
- [x] **k8s/base/kustomization.yaml**  
  - 이미지 태그: `latest` → `1.0.20` ✅
  - 버전 레이블: `1.0.17` → `1.0.20` ✅
- [x] **매니페스트 검증**: kubectl dry-run 성공 ✅

### ✅ 2. ArgoCD Application 설정 완료
- [x] **argocd/application.yaml**
  - Version 정보: `1.0.17` → `1.0.20` ✅
  - syncPolicy 설정: selfHeal=true, prune=true ✅
  - 자동 동기화: 활성화됨 ✅
- [x] **argocd/project.yaml**: 검증 완료 ✅
- [x] **argocd-app.yaml**: 기본 설정 확인 완료 ✅

### ✅ 3. GitHub Actions 파이프라인 검증
- [x] **gitops-pipeline.yml**: CNCF 준수 파이프라인 확인 ✅
- [x] **deploy.yaml**: Watchtower 자동배포 파이프라인 확인 ✅
- [x] **보안 스캔**: Bandit, Trivy 통합 완료 ✅
- [x] **테스트 단계**: Unit, Integration, API 테스트 분리 ✅

### ✅ 4. 환경 설정 파일 생성 완료
- [x] **.env.k8s**: GitOps 환경변수 설정 완료 ✅
- [x] **docs/github-secrets.md**: 필요한 secrets 문서화 완료 ✅
- [x] **보안 기본값**: FORCE_DISABLE_COLLECTION=true ✅

### ⚠️ 5. 필수 GitHub Secrets 설정 필요

#### 🐳 Docker Registry
- [ ] **DOCKER_REGISTRY_USER**: `jclee94`
- [ ] **DOCKER_REGISTRY_PASS**: `[설정 필요]`

#### 🔑 ArgoCD
- [ ] **ARGOCD_TOKEN**: `[설정 필요]`

#### 🔐 GitHub  
- [ ] **PAT_TOKEN**: `[설정 필요]`

#### 🏗️ 애플리케이션 시크릿
- [ ] **SECRET_KEY**: `[설정 필요]`
- [ ] **JWT_SECRET_KEY**: `[설정 필요]`

#### 📊 외부 API (선택사항)
- [ ] **REGTECH_USERNAME**: `[설정 필요]`
- [ ] **REGTECH_PASSWORD**: `[설정 필요]`
- [ ] **SECUDIUM_USERNAME**: `[설정 필요]`  
- [ ] **SECUDIUM_PASSWORD**: `[설정 필요]`

## 🛠️ 즉시 실행 가능한 배포 단계

### 1단계: GitHub Secrets 설정
```bash
# 필수 secrets 설정
gh secret set DOCKER_REGISTRY_USER --body "jclee94"
gh secret set DOCKER_REGISTRY_PASS --body "YOUR_REGISTRY_PASSWORD"
gh secret set ARGOCD_TOKEN --body "YOUR_ARGOCD_TOKEN" 
gh secret set PAT_TOKEN --body "YOUR_PAT_TOKEN"

# 애플리케이션 secrets (랜덤 생성)
gh secret set SECRET_KEY --body "$(openssl rand -hex 32)"
gh secret set JWT_SECRET_KEY --body "$(openssl rand -hex 32)"
```

### 2단계: 변경사항 커밋 및 푸시
```bash
# K8s 매니페스트와 ArgoCD 설정 커밋
git add k8s/ argocd/ .env.k8s docs/
git commit -m "feat: update container image to 1.0.20 for GitOps deployment

🚀 GitOps 배포 준비:
- K8s 매니페스트 이미지 태그 1.0.20으로 업데이트  
- ArgoCD Application 버전 정보 업데이트
- GitOps 환경 설정 파일 추가
- GitHub Secrets 문서화

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

### 3단계: ArgoCD 동기화 확인  
```bash
# ArgoCD 애플리케이션 상태 확인
argocd app get blacklist-app

# 수동 동기화 트리거 (필요시)
argocd app sync blacklist-app
```

## 📊 배포 후 검증 항목

### 🏥 헬스체크
- [ ] **기본 헬스체크**: `https://blacklist.jclee.me/health`
- [ ] **API 기능**: `https://blacklist.jclee.me/api/blacklist/active`  
- [ ] **Redis 연결**: 캐시 동작 확인
- [ ] **데이터베이스**: SQLite 파일 마운트 확인

### ☸️ Kubernetes 상태
- [ ] **Pod 상태**: `kubectl get pods -n blacklist-system`
- [ ] **서비스 상태**: `kubectl get svc -n blacklist-system`
- [ ] **인그레스 상태**: `kubectl get ingress -n blacklist-system`
- [ ] **HPA 상태**: `kubectl get hpa -n blacklist-system`

### 🔄 ArgoCD 상태
- [ ] **동기화 상태**: Synced
- [ ] **헬스 상태**: Healthy  
- [ ] **배포 히스토리**: 이전 버전 롤백 가능 여부
- [ ] **리소스 상태**: 모든 리소스 정상 배포

## 🚨 긴급 롤백 절차

### ArgoCD를 통한 롤백
```bash
# 이전 버전으로 롤백
argocd app rollback blacklist-app

# 특정 리비전으로 롤백  
argocd app rollback blacklist-app --revision=<PREVIOUS_REVISION>
```

### kubectl을 통한 긴급 롤백
```bash
# Deployment 롤백
kubectl rollout undo deployment/blacklist-deployment -n blacklist-system

# 롤백 상태 확인
kubectl rollout status deployment/blacklist-deployment -n blacklist-system
```

## 📈 모니터링 및 알림

### 📊 주요 메트릭
- **응답 시간**: < 500ms
- **CPU 사용률**: < 70%  
- **메모리 사용률**: < 80%
- **에러율**: < 1%

### 🔍 로그 모니터링
```bash
# 애플리케이션 로그
kubectl logs -f deployment/blacklist-deployment -n blacklist-system

# ArgoCD 로그 
kubectl logs -f -n argocd -l app.kubernetes.io/name=argocd-application-controller
```

## ✅ 배포 완료 확인

배포가 성공적으로 완료되면 다음을 확인하세요:

1. **✅ 애플리케이션 접근 가능**: https://blacklist.jclee.me
2. **✅ API 엔드포인트 동작**: `/api/health`, `/api/blacklist/active`
3. **✅ ArgoCD에서 Healthy 상태**: https://argo.jclee.me
4. **✅ 모든 Pod가 Running 상태**
5. **✅ 로그에 에러 없음**

---

**💡 팁**: 
- 첫 배포 시에는 `FORCE_DISABLE_COLLECTION=true`로 설정하여 외부 API 호출을 비활성화합니다
- 프로덕션 환경에서는 반드시 보안 스캔을 통과한 이미지만 배포합니다
- ArgoCD의 자동 동기화가 활성화되어 있으므로 Git 커밋 후 5분 내에 자동 배포됩니다