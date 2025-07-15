# GitHub Secrets 및 변수 설정 가이드

## 필수 GitHub Secrets 설정

GitHub Repository → Settings → Secrets and variables → Actions에서 다음 시크릿을 설정하세요:

### 1. Docker Registry 관련
```bash
# Docker Registry 인증 정보
REGISTRY_USERNAME=admin
REGISTRY_PASSWORD=bingogo1

# 또는 Docker Hub 사용 시
DOCKER_USERNAME=your-docker-username
DOCKER_PASSWORD=your-docker-password
```

### 2. Charts 리포지토리 관련
```bash
# charts.jclee.me 리포지토리 접근을 위한 GitHub Token
CHARTS_REPO_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

**GitHub Token 생성 방법:**
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. 권한 선택:
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows)
4. 생성된 토큰을 `CHARTS_REPO_TOKEN`에 입력

### 3. ArgoCD 관련
```bash
# ArgoCD API 토큰
ARGOCD_TOKEN=your-argocd-token

# ArgoCD 서버 URL (Variables에 설정)
ARGOCD_URL=https://argo.jclee.me
```

**ArgoCD Token 생성 방법:**
```bash
# ArgoCD CLI로 토큰 생성
argocd account generate-token --account ci-cd --id github-actions
```

### 4. 애플리케이션 시크릿
```bash
# Flask 애플리케이션 시크릿
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# REGTECH 인증 정보
REGTECH_USERNAME=nextrade
REGTECH_PASSWORD=Sprtmxm1@3

# SECUDIUM 인증 정보
SECUDIUM_USERNAME=nextrade
SECUDIUM_PASSWORD=Sprtmxm1@3
```

### 5. 알림 관련 (선택사항)
```bash
# 배포 알림을 위한 웹훅 URL
DEPLOYMENT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

## GitHub Variables 설정

Repository → Settings → Secrets and variables → Actions → Variables에서 설정:

### 1. 서비스 URL
```bash
SERVICE_URL=https://blacklist.jclee.me
ARGOCD_URL=https://argo.jclee.me
```

### 2. 환경 설정
```bash
ENVIRONMENT=production
PYTHON_VERSION=3.11
```

## 시크릿 확인 방법

설정이 올바른지 확인하기 위해 다음 명령어를 실행하세요:

```bash
# GitHub CLI 사용
gh secret list

# 또는 웹에서 확인
echo "https://github.com/$(git config --get remote.origin.url | sed 's|.*github.com[/:]||' | sed 's|\.git$||')/settings/secrets/actions"
```

## 보안 고려사항

1. **시크릿 순환**: 정기적으로 시크릿을 업데이트하세요
2. **최소 권한**: 토큰에 필요한 최소 권한만 부여하세요
3. **로깅 제한**: 시크릿이 로그에 출력되지 않도록 주의하세요
4. **환경 분리**: 개발/스테이징/프로덕션 환경별로 시크릿을 분리하세요

## 환경별 시크릿 관리

### Development 환경
```bash
# 개발 환경용 시크릿 (접두사 DEV_)
DEV_REGISTRY_USERNAME=dev-admin
DEV_REGISTRY_PASSWORD=dev-password
```

### Production 환경
```bash
# 프로덕션 환경용 시크릿 (접두사 PROD_)
PROD_REGISTRY_USERNAME=prod-admin
PROD_REGISTRY_PASSWORD=prod-password
```

## 트러블슈팅

### 1. CHARTS_REPO_TOKEN 권한 오류
```bash
# 에러: permission denied
# 해결: GitHub Token 권한 확인
# - repo 권한 필요
# - workflow 권한 필요
```

### 2. Registry 접근 오류
```bash
# 에러: authentication failed
# 해결: registry.jclee.me 인증 정보 확인
# - REGISTRY_USERNAME: admin
# - REGISTRY_PASSWORD: bingogo1
```

### 3. ArgoCD 동기화 실패
```bash
# 에러: permission denied
# 해결: ArgoCD 토큰 확인
# argocd account generate-token --account ci-cd
```

## 자동화 스크립트

시크릿 설정을 자동화하려면:

```bash
# GitHub CLI로 시크릿 설정
gh secret set REGISTRY_USERNAME --body "admin"
gh secret set REGISTRY_PASSWORD --body "bingogo1"
gh secret set CHARTS_REPO_TOKEN --body "ghp_xxxxxxxxxxxxxxxxxxxx"

# Variables 설정
gh variable set SERVICE_URL --body "https://blacklist.jclee.me"
gh variable set ARGOCD_URL --body "https://argo.jclee.me"
```

## 시크릿 검증

CI/CD 파이프라인에서 시크릿이 올바르게 설정되었는지 확인:

```yaml
# .github/workflows/ci-cd.yml에서 확인
- name: Verify Secrets
  run: |
    [[ -n "${{ secrets.REGISTRY_USERNAME }}" ]] || echo "❌ REGISTRY_USERNAME not set"
    [[ -n "${{ secrets.REGISTRY_PASSWORD }}" ]] || echo "❌ REGISTRY_PASSWORD not set"
    [[ -n "${{ secrets.CHARTS_REPO_TOKEN }}" ]] || echo "❌ CHARTS_REPO_TOKEN not set"
    echo "✅ All required secrets are set"
```

이 가이드를 따라 모든 시크릿과 변수를 설정하면 CI/CD 파이프라인이 정상적으로 작동합니다.