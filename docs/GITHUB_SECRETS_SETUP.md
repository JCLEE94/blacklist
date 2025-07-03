# GitHub Secrets 설정 가이드

CI/CD 파이프라인이 정상 작동하려면 다음 GitHub Secrets를 설정해야 합니다.

## 필수 Secrets

### 1. Registry 인증 정보
GitHub 저장소 → Settings → Secrets and variables → Actions에서 다음 secrets를 추가하세요:

```bash
REGISTRY_USERNAME=qws9411
REGISTRY_PASSWORD=bingogo1
```

### 2. Secrets 설정 방법

#### GitHub 웹 인터페이스에서:
1. GitHub 저장소로 이동
2. Settings 탭 클릭
3. 왼쪽 메뉴에서 "Secrets and variables" → "Actions" 클릭
4. "New repository secret" 버튼 클릭
5. 다음 secrets를 하나씩 추가:

| Name | Value | 설명 |
|------|-------|------|
| `REGISTRY_USERNAME` | `qws9411` | registry.jclee.me 사용자명 |
| `REGISTRY_PASSWORD` | `bingogo1` | registry.jclee.me 비밀번호 |

#### GitHub CLI로 설정:
```bash
# GitHub CLI 설치 및 로그인 후
gh secret set REGISTRY_USERNAME -b "qws9411"
gh secret set REGISTRY_PASSWORD -b "bingogo1"
```

## 파이프라인 작동 방식

1. **Push to main** → GitHub Actions 트리거
2. **Test** → 애플리케이션 테스트 실행
3. **Build** → Docker 이미지 빌드
4. **Push** → registry.jclee.me에 이미지 푸시
5. **Deploy** → Watchtower가 자동으로 새 이미지 감지하여 배포

## 확인 방법

Secrets가 올바르게 설정되었는지 확인하려면:

1. GitHub 저장소의 Actions 탭에서 워크플로우 실행 확인
2. Build 단계에서 registry 로그인 성공 확인
3. 배포 후 애플리케이션 정상 동작 확인

## 트러블슈팅

### Registry 로그인 실패
- REGISTRY_USERNAME, REGISTRY_PASSWORD가 정확히 설정되었는지 확인
- registry.jclee.me 서버 상태 확인

### 이미지 푸시 실패
- Docker 빌드 로그 확인
- 멀티 아키텍처 빌드 지원 여부 확인

### 배포 실패
- Watchtower 컨테이너 상태 확인
- kubectl 명령어 권한 확인