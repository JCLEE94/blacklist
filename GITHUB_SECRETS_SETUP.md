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

### 3. Brave Search API Key (선택사항)
```
Name: BRAVE_API_KEY  
Value: [Brave Search API 키]
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

- **filesystem**: 파일 시스템 접근
- **memory**: 메모리 기반 컨텍스트 저장
- **github**: GitHub API 통합
- **brave-search**: 웹 검색 기능

## 주의사항

1. **API 키 보안**: Secrets는 절대 코드에 직접 작성하지 마세요
2. **멘션 필수**: `@claude`를 반드시 포함해야 동작합니다
3. **명확한 요청**: 구체적이고 명확한 지시를 제공하세요
4. **한국어 지원**: 한국어로 요청하면 한국어로 응답합니다

## 트러블슈팅

- **403 에러**: ANTHROPIC_API_KEY 확인
- **응답 없음**: @claude 멘션 확인
- **권한 에러**: GitHub Token 권한 확인