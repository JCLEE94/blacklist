---
metadata:
  name: "init"
  version: "1.0.0"
  category: "core"
  description: "Project initialization and MCP tools setup"
  dependencies: []
  estimated_time: "15-30s"

execution:
  parallel_safe: true
  retry_count: 2
  timeout: "2m"

success_criteria:
  - "Serena project activated"
  - "Project rules initialized"
  - "Basic file structure created"

failure_recovery:
  - step: "Retry project activation"
    command: "mcp__serena__activate_project('.')"
  - step: "Manual mode switch"
    command: "mcp__serena__switch_modes(['editing', 'interactive'])"
---

# /init - Project Initialization

## 🎯 AI AGENT 실행 지시사항

### 핵심 미션
Claude Commands 프로젝트의 MCP 도구 환경을 초기화하고 기본 구조를 설정

### 실행 동기
모든 후속 명령어 실행을 위한 필수 기반 환경 구축

### 성공 기준
1. Serena MCP 서버 활성화 완료
2. 프로젝트 규칙 초기화 완료
3. 기본 환경 파일(.env, .gitignore) 생성 완료

**Execute MCP tools to initialize project:**

```python
# 1. Activate Serena project
mcp__serena__activate_project('.')
mcp__serena__switch_modes(['editing', 'interactive'])

# 2. Check onboarding status
mcp__serena__check_onboarding_performed()

# 3. Initialize project rules
mcp__shrimp_task_manager__init_project_rules()

# 4. Create basic structure
mcp__serena__create_text_file('.env', 'NODE_ENV=development\nPORT=3000')
mcp__serena__create_text_file('.gitignore', 'node_modules/\n.env\nlogs/')

# 5. Plan next step: /auth
print("✅ Project initialized → Run /auth next")
```
- Serena 프로젝트 활성화

## 실행 과정
1. **환경 설정**: npm run env:setup
2. **의존성 설치**: npm install
3. **기본 설정**: npm run setup
4. **Serena 활성화**: mcp__serena__activate_project('.')
5. **검증**: npm run validate

## 자동 생성 파일
- .env.dev: 개발 환경 설정
- .env.prod: 프로덕션 환경 설정
- agent-config.json: Agent 설정
- mcp-tools-config.json: MCP 도구 설정

## 필수 환경 변수
- ARGOCD_TOKEN: ArgoCD API 인증
- GITHUB_TOKEN: GitHub PAT
- REGISTRY_PASSWORD: Docker 레지스트리
- MONGODB_URI: MongoDB 연결
- JWT_ACCESS_SECRET: JWT 액세스 토큰
- JWT_REFRESH_SECRET: JWT 리프레시 토큰

## 검증 단계
- 서비스 연결성 테스트
- 인증 시스템 검증
- GitOps 파이프라인 준비 상태 확인

## 연계 명령어
- /auth: 인증 시스템 설정
- /config: 세부 설정 관리