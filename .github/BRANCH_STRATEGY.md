# 🌳 Blacklist System Branch Strategy

## Git Flow 기반 브랜치 전략

### 브랜치 구조

```
main (production)
├── develop (integration)
├── staging (pre-production)
├── feature/* (feature development)
├── hotfix/* (emergency fixes)
└── release/* (release preparation)
```

## 주요 브랜치

### 1. `main` - 프로덕션 브랜치
- **목적**: 실제 운영 환경 배포
- **보호**: 직접 푸시 금지, PR을 통한 병합만 허용
- **배포**: 자동 배포 (GitHub Actions)
- **버전**: Git 태그를 통한 릴리즈 관리

### 2. `develop` - 개발 통합 브랜치
- **목적**: 기능 개발 통합 및 테스트
- **병합**: feature 브랜치들이 병합됨
- **배포**: 개발 환경 자동 배포
- **규칙**: 항상 배포 가능한 상태 유지

### 3. `staging` - 스테이징 브랜치
- **목적**: 운영 환경과 동일한 조건에서 최종 테스트
- **배포**: 스테이징 환경 자동 배포
- **QA**: 품질 보증 테스트 수행
- **승인**: 운영 배포 전 최종 검증

## 보조 브랜치

### 4. `feature/*` - 기능 개발 브랜치
- **네이밍**: `feature/기능명-이슈번호`
- **예시**: `feature/dynamic-version-12`, `feature/security-auth-34`
- **생성**: `develop`에서 분기
- **병합**: `develop`으로 PR을 통해 병합
- **삭제**: 병합 후 자동 삭제

### 5. `hotfix/*` - 긴급 수정 브랜치
- **네이밍**: `hotfix/수정내용-이슈번호`
- **예시**: `hotfix/security-fix-56`, `hotfix/memory-leak-78`
- **생성**: `main`에서 분기
- **병합**: `main`과 `develop` 양쪽에 병합
- **배포**: 즉시 운영 배포

### 6. `release/*` - 릴리즈 준비 브랜치
- **네이밍**: `release/v1.0.0`
- **생성**: `develop`에서 분기
- **용도**: 릴리즈 준비, 버전 업데이트, 문서화
- **병합**: `main`과 `develop`에 병합

## 워크플로우

### 기능 개발 플로우
```bash
# 1. develop에서 feature 브랜치 생성
git checkout develop
git pull origin develop
git checkout -b feature/new-analytics-45

# 2. 개발 작업 수행
git add .
git commit -m "feat: implement real-time analytics dashboard"

# 3. 원격 브랜치에 푸시
git push origin feature/new-analytics-45

# 4. Pull Request 생성 (develop ← feature/new-analytics-45)
# 5. 코드 리뷰 및 CI/CD 통과 후 병합
# 6. 브랜치 자동 삭제
```

### 긴급 수정 플로우
```bash
# 1. main에서 hotfix 브랜치 생성
git checkout main
git pull origin main
git checkout -b hotfix/security-vulnerability-67

# 2. 긴급 수정 작업
git add .
git commit -m "fix: resolve critical security vulnerability"

# 3. main으로 PR 생성 및 병합
# 4. develop으로도 병합 (자동 또는 수동)
# 5. 즉시 운영 배포
```

## GitHub Actions 브랜치별 배포 전략

### Main 브랜치 (Production)
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy-production:
    runs-on: self-hosted
    environment: production
```

### Develop 브랜치 (Development)
```yaml
on:
  push:
    branches: [develop]

jobs:
  deploy-development:
    runs-on: ubuntu-latest
    environment: development
```

### Staging 브랜치 (Staging)
```yaml
on:
  push:
    branches: [staging]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
```

## 브랜치 보호 규칙

### Main 브랜치 보호
- ✅ Require pull request reviews (2명 이상)
- ✅ Require status checks to pass
- ✅ Require branches to be up to date
- ✅ Restrict pushes that create files over 100MB
- ✅ Require signed commits

### Develop 브랜치 보호
- ✅ Require pull request reviews (1명 이상)
- ✅ Require status checks to pass
- ✅ Dismiss stale reviews

### Staging 브랜치 보호
- ✅ Require pull request reviews (1명)
- ✅ Require status checks to pass

## 커밋 메시지 컨벤션

### 형식
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Type 분류
- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 수정
- `style`: 코드 포매팅, 세미콜론 누락 등
- `refactor`: 코드 리팩토링
- `perf`: 성능 개선
- `test`: 테스트 코드 추가/수정
- `chore`: 빌드 프로세스 수정, 패키지 매니저 설정 등
- `ci`: CI/CD 설정 수정
- `security`: 보안 관련 수정

### 예시
```
feat(auth): implement JWT token refresh mechanism

- Add automatic token refresh logic
- Update authentication middleware
- Add refresh token validation

Closes #123
```

## 릴리즈 관리

### 시맨틱 버저닝 (Semantic Versioning)
- **Major** (1.0.0): 호환성이 깨지는 변경
- **Minor** (1.1.0): 하위 호환되는 기능 추가
- **Patch** (1.1.1): 하위 호환되는 버그 수정

### 릴리즈 프로세스
1. `develop`에서 `release/v1.1.0` 브랜치 생성
2. 버전 번호 업데이트, CHANGELOG 작성
3. QA 테스트 및 버그 수정
4. `main`으로 병합 후 Git 태그 생성
5. GitHub Release 생성 및 배포 노트 작성

## 환경별 배포 URL

### 운영 환경 (Production)
- **URL**: https://blacklist.jclee.me
- **브랜치**: `main`
- **배포**: GitHub Actions (self-hosted runner)

### 스테이징 환경 (Staging)
- **URL**: https://staging-blacklist.jclee.me
- **브랜치**: `staging`
- **배포**: GitHub Actions (ubuntu-latest)

### 개발 환경 (Development)
- **URL**: https://dev-blacklist.jclee.me
- **브랜치**: `develop`
- **배포**: GitHub Actions (ubuntu-latest)

## 팀 협업 규칙

### Code Review 규칙
- 모든 PR은 코드 리뷰 필수
- 리뷰어는 24시간 내 리뷰 완료
- 컨플릭트 해결은 PR 작성자 책임
- CI/CD 통과 후 병합 가능

### 브랜치 네이밍 규칙
- feature: `feature/기능명-이슈번호`
- hotfix: `hotfix/수정내용-이슈번호`
- release: `release/v버전번호`
- 케밥 케이스 사용 (kebab-case)

### 이슈 관리
- GitHub Issues를 통한 작업 추적
- 라벨을 통한 분류 (bug, enhancement, documentation)
- 마일스톤을 통한 릴리즈 관리
- 브랜치명에 이슈 번호 포함 필수

---

📅 **최종 업데이트**: 2025-08-28
🏗️ **적용 버전**: v1.0.1438+
🔄 **검토 주기**: 분기별 전략 검토 및 개선