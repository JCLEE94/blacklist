# GitHub Secrets 설정 가이드

Claude Code Action을 사용하기 위해 다음 Secrets를 GitHub 저장소에 설정해야 합니다.

## 필수 Secrets

### 1. Anthropic API Key
```
Name: ANTHROPIC_API_KEY
Value: [Anthropic API 키]
```

### 2. GitHub Token (자동 제공)
```
Name: GITHUB_TOKEN
Value: [GitHub에서 자동 제공 - 설정 불필요]
```

### 3. Brave Search API Key (선택사항 - 웹 검색 기능)
```
Name: BRAVE_API_KEY  
Value: [Brave Search API 키 - https://brave.com/search/api/]
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

## MCP (Model Context Protocol) 기능

현재 워크플로우에 설정된 MCP 서버들:

- **filesystem**: 프로젝트 파일 읽기/쓰기/편집 (`/github/workspace`)
- **memory**: 컨텍스트 기억 및 지식 그래프 생성
- **sequential-thinking**: 복잡한 문제 단계별 사고 과정
- **brave-search**: 실시간 웹 검색 (API 키 필요)

### MCP 도구 사용법

Claude가 다음과 같은 고급 기능을 사용할 수 있습니다:

```
@claude 프로젝트의 모든 Python 파일을 스캔해서 보안 취약점을 찾아주세요.
# → filesystem MCP로 모든 .py 파일 읽고 분석

@claude 이 이슈와 관련된 이전 토론 내용을 기억하고 있나요?
# → memory MCP로 컨텍스트 저장/검색

@claude 이 복잡한 아키텍처 문제를 단계별로 분석해주세요.
# → sequential-thinking MCP로 체계적 사고

@claude 최신 Flask 보안 패치에 대해 검색해주세요.
# → brave-search MCP로 실시간 웹 검색
```

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

**현재 활성 워크플로우**: `ci-optimized.yml` (주 CI/CD 파이프라인)

### MCP 서버 상태 확인
```bash
# GitHub Actions 로그에서 MCP 서버 초기화 확인
# "MCP server 'filesystem' started successfully" 메시지 확인
```