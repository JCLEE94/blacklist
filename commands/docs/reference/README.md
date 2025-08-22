# 🤖 AI Agents - 표준화된 에이전트 시스템

## 🏷️ 표준화된 명명 규칙

모든 에이전트는 **역할-기능-영역** 패턴을 따릅니다:

### 📂 역할 카테고리
- **orchestrator**: 🎯 시스템 전체 조정 및 관리
- **assistant**: 💡 지능형 도우미 및 상담
- **executor**: ⚡ 명령 실행 및 작업 수행
- **guardian**: 🛡️ 품질 및 보안 수호
- **coordinator**: 🔄 협업 및 동기화 조정
- **analyzer**: 📊 분석 및 진단
- **runner**: 🏃 자동화 실행
- **cleaner**: 🧹 정리 및 최적화
- **specialist**: 🔧 전문 기술 특화

### 🎯 표준화된 에이전트 목록

#### 관리 (Management)
- `orchestrator-master-system`: 전체 시스템 총괄 관리
- `orchestrator-workflow-automation`: 워크플로우 자동화 조정
- `coordinator-adaptive-intelligence`: 적응형 지능 조정

#### 지능형 (Intelligence)
- `assistant-intelligent-query`: 자연어 이해 및 제안
- `analyzer-project-state`: 프로젝트 상태 분석

#### 실행 (Execution)
- `executor-command-system`: 명령어 실행 전문
- `runner-test-automation`: 테스트 자동화 실행

#### 전문화 (Specialized)
- `guardian-quality-project`: 품질 및 보안 수호
- `specialist-deployment-infra`: 배포 인프라 전문
- `specialist-github-cicd`: GitHub/CI/CD 전문

#### 유지보수 (Maintenance)
- `cleaner-code-quality`: 코드 품질 정리

## 🚀 사용 방법

### 1. 에이전트 실행기 사용
```bash
# 에이전트 목록 (카테고리별)
python agent-runner.py --list

# 특정 에이전트 실행
python agent-runner.py orchestrator-master-system "전체 프로젝트 정리"
python agent-runner.py guardian-quality-project "코드 품질 개선"
python agent-runner.py analyzer-project-state "현재 상태 분석"
```

### 2. Auto 시스템 통합
```bash
# Auto 시스템이 자동으로 적절한 에이전트 선택
./commands/auto/auto.md

# 특정 작업에 에이전트 활용
source ./commands/auto/agent-integration.md
execute_agent_for_task "analysis" "프로젝트 전체 분석"
```

## 📋 에이전트별 호환 명령어

- **orchestrator-master-system**: auto, clean, test, commit, create-pr
- **guardian-quality-project**: clean, test, review
- **executor-command-system**: clean, test, commit, create-pr, gitops
- **runner-test-automation**: test
- **cleaner-code-quality**: clean
- **specialist-deployment-infra**: gitops, hotfix
- **specialist-github-cicd**: create-pr, fix-issue

## 🔧 시스템 통합

### Commands 시스템 연동
- 각 에이전트는 호환되는 `/commands/` 명령어와 자동 연동
- Auto 시스템에서 상황에 맞는 에이전트 자동 선택
- 에이전트 실행 결과가 commands 워크플로우에 반영

### 메타데이터 관리
- `agent-registry.json`: 모든 에이전트 메타데이터
- 역할, 기능, 영역별 분류
- 의존성 및 호환성 정보
- 우선순위 및 실행 순서

## 📈 개선 사항

1. **명확한 역할 구분**: 역할-기능-영역 패턴으로 목적 명확화
2. **체계적 분류**: 카테고리별 관리 및 우선순위 시스템
3. **자동 통합**: Commands 시스템과 자연스러운 연동
4. **메타데이터 기반**: JSON 레지스트리로 확장 가능한 관리
5. **향상된 UX**: 카테고리별 목록 및 직관적 실행

---

**"표준화된 AI 에이전트로 더 체계적이고 효율적인 개발 워크플로우"**
