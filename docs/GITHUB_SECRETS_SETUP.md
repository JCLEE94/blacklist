# GitHub Secrets 설정 가이드

## 필수 GitHub Secrets

GitHub Repository → Settings → Secrets and variables → Actions에서 다음 secrets를 추가하세요:

### 1. Docker Registry Secrets
```
DOCKER_REGISTRY_USER: admin
DOCKER_REGISTRY_PASS: bingogo1
```

### 2. Helm Repository Secrets
```
HELM_REPO_USERNAME: admin
HELM_REPO_PASSWORD: bingogo1
```

### 3. 통합 인증 (선택사항)
```
REGISTRY_USERNAME: admin
REGISTRY_PASSWORD: bingogo1
```

## GitHub CLI를 사용한 설정

```bash
# GitHub CLI 설치 확인
gh --version

# Secrets 설정
gh secret set DOCKER_REGISTRY_USER -b "admin"
gh secret set DOCKER_REGISTRY_PASS -b "bingogo1"
gh secret set HELM_REPO_USERNAME -b "admin"
gh secret set HELM_REPO_PASSWORD -b "bingogo1"
gh secret set REGISTRY_USERNAME -b "admin"
gh secret set REGISTRY_PASSWORD -b "bingogo1"

# Secrets 목록 확인
gh secret list
```

## 수동 설정 방법

1. GitHub 저장소로 이동
2. Settings 탭 클릭
3. 좌측 메뉴에서 "Secrets and variables" → "Actions" 클릭
4. "New repository secret" 버튼 클릭
5. 각 secret 추가:
   - Name: `DOCKER_REGISTRY_USER`
   - Secret: `admin`
   - "Add secret" 클릭
6. 모든 secrets에 대해 반복

## CI/CD에서 사용

```yaml
# Docker 로그인
- name: Login to Docker Registry
  run: |
    echo "${{ secrets.DOCKER_REGISTRY_PASS }}" | docker login registry.jclee.me \
      --username "${{ secrets.DOCKER_REGISTRY_USER }}" \
      --password-stdin

# Helm 차트 푸시
- name: Push Helm Chart
  env:
    HELM_USERNAME: ${{ secrets.HELM_REPO_USERNAME }}
    HELM_PASSWORD: ${{ secrets.HELM_REPO_PASSWORD }}
  run: |
    curl --data-binary "@chart.tgz" \
      -u "${HELM_USERNAME}:${HELM_PASSWORD}" \
      https://charts.jclee.me/api/charts
```

## 로컬 환경 변수 설정

개발 환경에서 사용하려면 `.env` 파일 생성:

```bash
# .env (Git에 추가하지 마세요!)
export DOCKER_REGISTRY_USER=admin
export DOCKER_REGISTRY_PASS=bingogo1
export HELM_REPO_USERNAME=admin
export HELM_REPO_PASSWORD=bingogo1
export REGISTRY_USERNAME=admin
export REGISTRY_PASSWORD=bingogo1

# 환경 변수 로드
source .env
```

## 인증 테스트

```bash
# 테스트 스크립트 실행
./scripts/test-auth-services.sh
```

## 보안 주의사항

1. **절대 코드에 직접 패스워드를 입력하지 마세요**
2. `.env` 파일은 `.gitignore`에 추가하세요
3. 프로덕션에서는 더 강력한 패스워드 사용을 권장합니다
4. 가능하면 토큰 기반 인증을 사용하세요
5. 정기적으로 패스워드를 변경하세요