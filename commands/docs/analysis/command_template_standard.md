# 표준 명령어 템플릿

모든 명령어 파일은 다음 구조를 따라야 함:

```yaml
---
metadata:
  name: "명령어명"
  version: "1.0.0"
  category: "core|dev|infra|utils|auto"
  description: "명령어 설명"
  dependencies: ["필요한 선행 명령어들"]
  estimated_time: "예상 소요 시간"

execution:
  parallel_safe: true|false
  retry_count: 3
  timeout: "5m"

success_criteria:
  - "성공 판단 기준 1"
  - "성공 판단 기준 2"

failure_recovery:
  - step: "복구 단계 1"
    command: "실행할 명령"
  - step: "복구 단계 2"
    command: "실행할 명령"
---

# 명령어명 - 설명

## 🎯 AI AGENT 실행 지시사항

### 핵심 미션
[구체적인 실행 목표]

### 실행 동기
[왜 이 작업이 중요한가]

### 성공 기준
[명확한 성공 판단 기준]

### 실행 단계
[구체적인 실행 절차]

### 에러 처리
[예상 오류 및 대응 방안]
```