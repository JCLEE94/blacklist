# GitHub Secrets 설정 가이드

## 빠른 설정 단계

### 1. GitHub 저장소 Settings 페이지로 이동
https://github.com/jclee/blacklist/settings/secrets/actions

### 2. 필수 시크릿 추가

#### REGISTRY_USERNAME
1. "New repository secret" 버튼 클릭
2. Name: `REGISTRY_USERNAME`
3. Value: `admin`
4. "Add secret" 클릭

#### REGISTRY_PASSWORD  
1. "New repository secret" 버튼 클릭
2. Name: `REGISTRY_PASSWORD`
3. Value: `bingogo1`
4. "Add secret" 클릭

## 확인 사항

설정 완료 후 다음과 같이 표시되어야 합니다:

```
Repository secrets (2)
- REGISTRY_USERNAME    Updated just now
- REGISTRY_PASSWORD    Updated just now
```

## 테스트 방법

1. 코드 변경 후 commit & push:
```bash
git add .
git commit -m "test: registry authentication"
git push origin main
```

2. GitHub Actions 확인:
- https://github.com/jclee/blacklist/actions
- "GitOps Pipeline" 워크플로우 클릭
- "Build and push" 단계에서 Docker login 성공 확인

## 추가 시크릿 (선택사항)

필요시 다음 시크릿도 추가할 수 있습니다:

| Name | Value | 용도 |
|------|-------|------|
| REGTECH_USERNAME | nextrade | REGTECH 수집 |
| REGTECH_PASSWORD | Sprtmxm1@3 | REGTECH 수집 |
| SECUDIUM_USERNAME | nextrade | SECUDIUM 수집 |
| SECUDIUM_PASSWORD | Sprtmxm1@3 | SECUDIUM 수집 |
| CLOUDFLARE_TUNNEL_TOKEN | (토큰값) | Cloudflare Tunnel |
| CF_API_TOKEN | (API토큰) | Cloudflare DNS |

## 문제 해결

### Actions 실행 실패 시
1. Actions 탭에서 실패한 워크플로우 클릭
2. 에러 메시지 확인
3. 주로 다음 문제일 가능성:
   - 시크릿 이름 오타
   - 시크릿 값 누락
   - 권한 문제

### 시크릿 수정 방법
- 같은 이름으로 다시 생성하면 자동으로 덮어쓰기됩니다
- 삭제: 시크릿 이름 옆 🗑️ 아이콘 클릭

## 보안 주의사항
- 시크릿은 한 번 저장하면 값을 볼 수 없습니다
- 로그에 시크릿이 노출되지 않도록 주의
- 시크릿 값은 GitHub Actions 실행 시에만 사용됩니다