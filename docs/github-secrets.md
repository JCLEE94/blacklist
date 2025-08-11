# GitHub Secrets 설정 가이드

블랙리스트 관리 시스템의 GitOps 파이프라인에 필요한 GitHub Secrets 설정 문서입니다.

## 필수 Secrets 목록

### 🐳 Docker Registry 관련
- **DOCKER_REGISTRY_USER**: `jclee94` 
  - Docker Registry 사용자명
- **DOCKER_REGISTRY_PASS**: `[REGISTRY_PASSWORD]`
  - Docker Registry 비밀번호

### 🔑 ArgoCD 관련  
- **ARGOCD_TOKEN**: `[ARGOCD_API_TOKEN]`
  - ArgoCD API 토큰 (Applications 관리용)
- **ARGOCD_SERVER**: `argo.jclee.me`
  - ArgoCD 서버 주소 (이미 환경변수로 설정됨)

### 🔐 GitHub 관련
- **PAT_TOKEN**: `[PERSONAL_ACCESS_TOKEN]`
  - GitHub Personal Access Token (repo, write:packages 권한)
- **GITHUB_TOKEN**: `[AUTO_GENERATED]`
  - GitHub Actions 자동 생성 토큰

### 🏗️ 애플리케이션 시크릿
- **SECRET_KEY**: `[FLASK_SECRET_KEY]`
  - Flask 애플리케이션 시크릿 키
- **JWT_SECRET_KEY**: `[JWT_SECRET]`
  - JWT 토큰 서명용 시크릿

### 📊 외부 API 크리덴셜
- **REGTECH_USERNAME**: `[REGTECH_USER]`
  - REGTECH API 사용자명
- **REGTECH_PASSWORD**: `[REGTECH_PASS]`
  - REGTECH API 비밀번호
- **SECUDIUM_USERNAME**: `[SECUDIUM_USER]`
  - SECUDIUM API 사용자명  
- **SECUDIUM_PASSWORD**: `[SECUDIUM_PASS]`
  - SECUDIUM API 비밀번호

## Secret 생성 방법

### GitHub UI를 통한 설정
```
1. GitHub 저장소로 이동
2. Settings → Secrets and variables → Actions
3. "New repository secret" 클릭
4. Name과 Secret 입력 후 "Add secret" 클릭
```

### GitHub CLI를 통한 설정
```bash
# Docker Registry 크리덴셜
gh secret set DOCKER_REGISTRY_USER --body "jclee94"
gh secret set DOCKER_REGISTRY_PASS --body "YOUR_REGISTRY_PASSWORD"

# ArgoCD 토큰
gh secret set ARGOCD_TOKEN --body "YOUR_ARGOCD_TOKEN"

# Personal Access Token  
gh secret set PAT_TOKEN --body "YOUR_PAT_TOKEN"

# 애플리케이션 시크릿
gh secret set SECRET_KEY --body "$(openssl rand -hex 32)"
gh secret set JWT_SECRET_KEY --body "$(openssl rand -hex 32)"

# 외부 API 크리덴셜
gh secret set REGTECH_USERNAME --body "YOUR_REGTECH_USER"
gh secret set REGTECH_PASSWORD --body "YOUR_REGTECH_PASS"
gh secret set SECUDIUM_USERNAME --body "YOUR_SECUDIUM_USER"
gh secret set SECUDIUM_PASSWORD --body "YOUR_SECUDIUM_PASS"
```

## ArgoCD 토큰 생성 방법

### 1. ArgoCD CLI를 통한 토큰 생성
```bash
# ArgoCD 로그인
argocd login argo.jclee.me --username admin

# 토큰 생성 (30일 유효)
argocd account generate-token --account admin --id github-actions --exp 720h
```

### 2. ArgoCD 웹 UI를 통한 토큰 생성
```
1. https://argo.jclee.me 접속
2. Settings → Accounts
3. admin 계정 선택
4. "GENERATE NEW" 버튼 클릭
5. Token name: "github-actions"
6. Expires In: "30 days"
7. 생성된 토큰 복사
```

## Personal Access Token (PAT) 권한

GitHub PAT에 필요한 최소 권한:
- **repo**: Full control of private repositories
- **write:packages**: Upload packages to GitHub Package Registry  
- **read:packages**: Download packages from GitHub Package Registry
- **workflow**: Update GitHub Action workflows

## Kubernetes Secrets 매핑

GitOps 파이프라인이 자동으로 다음 K8s Secret을 생성합니다:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: blacklist-secrets
  namespace: blacklist-system
type: Opaque  
data:
  SECRET_KEY: <base64-encoded-value>
  JWT_SECRET_KEY: <base64-encoded-value>
  REGTECH_USERNAME: <base64-encoded-value>
  REGTECH_PASSWORD: <base64-encoded-value>
  SECUDIUM_USERNAME: <base64-encoded-value>
  SECUDIUM_PASSWORD: <base64-encoded-value>
```

## 보안 모범 사례

### 🔒 토큰 관리
- 토큰은 정기적으로 로테이션 (권장: 30일)
- 최소 권한 원칙 적용
- 토큰 노출 시 즉시 폐기 후 재생성

### 🛡️ 환경별 분리  
- 개발/스테이징/프로덕션 환경별 별도 크리덴셜 사용
- 환경별 GitHub Environments 설정 권장

### 📝 모니터링
- GitHub Actions 로그에서 시크릿 노출 여부 주기적 확인
- ArgoCD 감사 로그 모니터링
- 비정상적인 API 호출 패턴 감지

## 문제 해결

### Secret 관련 오류
```bash
# Secrets 목록 확인
gh secret list

# 특정 Secret 업데이트
gh secret set SECRET_NAME --body "NEW_VALUE"

# Secret 삭제
gh secret delete SECRET_NAME
```

### ArgoCD 연결 오류
```bash  
# ArgoCD 연결 테스트
curl -k -H "Authorization: Bearer $ARGOCD_TOKEN" \
  https://argo.jclee.me/api/v1/applications

# 토큰 유효성 검증
argocd account can-i sync applications --account admin
```

### Docker Registry 오류
```bash
# 레지스트리 로그인 테스트
docker login registry.jclee.me -u $DOCKER_REGISTRY_USER -p $DOCKER_REGISTRY_PASS

# 이미지 push 테스트  
docker build -t registry.jclee.me/test:latest .
docker push registry.jclee.me/test:latest
```

## 자동화된 Secret 검증

파이프라인에서 자동으로 실행되는 검증 단계:

```yaml
- name: Validate Secrets
  run: |
    # 필수 secrets 존재 여부 확인
    for secret in DOCKER_REGISTRY_USER DOCKER_REGISTRY_PASS ARGOCD_TOKEN; do
      if [ -z "${!secret}" ]; then
        echo "❌ Missing required secret: $secret"
        exit 1
      fi
    done
    echo "✅ All required secrets are configured"
```

---
**⚠️ 중요**: 이 문서의 시크릿 값들은 예시용입니다. 실제 프로덕션 환경에서는 강력한 임의 값을 사용하세요.