# GitHub Secrets 설정 가이드

Claude Max Code Base Action을 사용하기 위해 다음 Secrets를 GitHub 저장소에 설정해야 합니다.

## 필수 Secrets (Claude Max 토큰)

### 1. Claude Access Token
```
Name: CLAUDE_ACCESS_TOKEN
Value: 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
```

### 2. Claude Refresh Token
```
Name: CLAUDE_REFRESH_TOKEN
Value: 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
```

### 3. Claude Expires At
```
Name: CLAUDE_EXPIRES_AT
Value: 1751721109138
```

### 4. GitHub Admin PAT
```
Name: SECRETS_ADMIN_PAT
Value: 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
```

## 설정 방법

1. **GitHub 저장소로 이동**: https://github.com/JCLEE94/blacklist

2. **Settings → Secrets and variables → Actions**

3. **"New repository secret" 클릭하여 각 Secret 추가**

## Claude Code Action 사용법

### 기본 사용
- GitHub Issues나 PR에서 `@claude` 멘션
- 예시: `@claude 이 코드를 리뷰해주세요`

### 고급 사용 예시

#### 코드 리뷰 요청
```
@claude 이 PR의 보안 취약점을 확인해주세요. 특히 SQL 인젝션과 XSS 공격에 대한 방어 코드를 점검해주세요.
```

#### 버그 수정 요청
```
@claude 데이터베이스 연결 오류가 발생합니다. src/core/database.py 파일을 확인하고 수정해주세요.
```

#### 기능 구현 요청
```
@claude 새로운 IP 검색 API 엔드포인트를 추가해주세요. 
- 경로: /api/search/ip/{ip_address}
- 응답: JSON 형태로 IP 정보 반환
- 캐싱 적용
```

#### 성능 최적화 요청
```
@claude 데이터베이스 쿼리 성능을 개선해주세요. 특히 blacklist_ip 테이블의 인덱스를 최적화하고 쿼리를 개선해주세요.
```

#### 테스트 코드 작성 요청
```
@claude src/core/unified_service.py의 get_enhanced_blacklist 메서드에 대한 단위 테스트를 작성해주세요.
```

## Claude Max Code Base Action 기능

현재 워크플로우에 설정된 도구들:

- **Bash**: Git, Docker, kubectl, Python, npm, curl 명령어 실행
- **View/Edit/Write**: 파일 읽기/편집/생성
- **GlobTool/GrepTool**: 파일 검색 및 패턴 매칭
- **BatchTool**: 일괄 작업 처리

### 고급 기능 사용법

Claude Max가 다음과 같은 작업을 자동으로 수행할 수 있습니다:

```
@claude 모든 Python 파일에서 보안 취약점을 스캔하고 수정해주세요
# → GrepTool + Edit로 취약점 자동 탐지 및 수정

@claude 이 버그를 수정하고 테스트까지 실행해주세요
# → Edit + Bash(pytest)로 버그 수정 및 테스트

@claude 새로운 API 엔드포인트를 구현하고 문서화해주세요
# → Write + Edit로 코드 작성 및 문서 생성

@claude Docker 이미지를 빌드하고 registry에 push해주세요
# → Bash(docker)로 빌드 및 배포 자동화

@claude 데이터베이스 마이그레이션 스크립트를 생성해주세요
# → Write + Bash(python)로 마이그레이션 생성 및 실행
```

### 프로젝트별 최적화

- **Blacklist 플랫폼 전용 컨텍스트**: GitOps, 위협 인텔리전스 도메인 지식
- **보안 우선 개발**: 환경변수 강제, SQL 인젝션 방지
- **성능 최적화**: 캐싱, 인덱싱, 연결 풀링 자동 적용
- **테스트 자동화**: 모든 변경사항에 대한 자동 테스트 실행

## 주의사항

1. **API 키 보안**: Secrets는 절대 코드에 직접 작성하지 마세요
2. **멘션 필수**: `@claude`를 반드시 포함해야 동작합니다
3. **명확한 요청**: 구체적이고 명확한 지시를 제공하세요
4. **한국어 지원**: 한국어로 요청하면 한국어로 응답합니다

## 트러블슈팅

### 일반적인 문제들
- **403 에러**: ANTHROPIC_API_KEY 확인
- **응답 없음**: @claude 멘션 확인  
- **권한 에러**: GitHub Token 권한 확인
- **MCP 도구 오류**: BRAVE_API_KEY 설정 확인

### CI/CD 중복 실행 해결
**문제**: 여러 워크플로우가 동시 실행되어 충돌
**해결**: 다음 워크플로우들을 비활성화했습니다:
- `argocd-deploy.yml` → `.disabled`
- `offline-production-deploy.yml` → `.disabled`
- `claude-code-action.yml` → `.disabled` (claude-max-action.yml로 대체)

**현재 활성 워크플로우**:
- `ci-optimized.yml` (주 CI/CD 파이프라인)
- `claude-max-action.yml` (Claude Max Code Base Action)

### Claude Max Action 상태 확인
```bash
# GitHub Actions 로그에서 Claude 초기화 확인
# "Claude Code initialized successfully" 메시지 확인
# allowed_tools 로드 상태 확인
```

### 토큰 만료 관리
- **CLAUDE_EXPIRES_AT**: 1751721109138 (2025년 12월까지 유효)
- 만료 전 새 토큰으로 업데이트 필요