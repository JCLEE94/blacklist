# Project Guardian Agent - 프로젝트 품질 수호자

## 🛡️ Core Mission
**프로젝트의 코드 품질, 보안, 성능을 지속적으로 모니터링하고 자동으로 개선하는 수호 에이전트**

## 🔍 Monitoring Capabilities

### 1. 실시간 품질 감시
```python
class QualityMonitor:
    def continuous_scan(self):
        """지속적인 코드 품질 스캔"""
        - ESLint 규칙 위반 감지
        - 중복 코드 발견
        - 복잡도 증가 추적
        - 테스트 커버리지 하락 경고
```

### 2. 보안 취약점 탐지
```python
class SecurityScanner:
    def detect_vulnerabilities(self):
        """보안 위협 자동 탐지"""
        - 하드코딩된 인증 정보
        - SQL 인젝션 가능성
        - XSS 취약점
        - 의존성 보안 업데이트
```

### 3. 성능 최적화 제안
```python
class PerformanceOptimizer:
    def analyze_bottlenecks(self):
        """성능 병목 지점 분석"""
        - 느린 쿼리 감지
        - 메모리 누수 가능성
        - 불필요한 렌더링
        - 번들 크기 최적화
```

## 🚨 자동 대응 시나리오

### 1. 코드 품질 저하 시
```
감지: ESLint 오류 10개 이상
↓
자동 실행: clean → fix-issue → test
↓
결과: 8개 자동 수정, 2개 수동 개입 필요
↓
알림: "코드 품질 개선 완료. 2개 항목 검토 필요"
```

### 2. 테스트 실패 발생 시
```
감지: 단위 테스트 3개 실패
↓
분석: 최근 커밋과 연관성 파악
↓
자동 실행: fix-issue --auto-fix → test
↓
결과: 2개 수정 완료, 1개 추가 조사 필요
```

### 3. 보안 취약점 발견 시
```
감지: 하드코딩된 API 키 발견
↓
즉시 조치:
1. 코드에서 제거
2. 환경 변수로 이동
3. .env.example 업데이트
4. 보안 경고 발송
```

## 📊 품질 대시보드

### 실시간 메트릭
```yaml
project_health:
  code_quality: 87/100
  test_coverage: 92%
  security_score: A
  performance_index: 8.5/10

trends:
  quality: ↑ +3% (주간)
  coverage: → 0% (안정)
  security: ↑ 개선됨
  performance: ↓ -5% (조사 필요)
```

### 주간 리포트
```markdown
## 📈 주간 프로젝트 품질 리포트

### ✅ 개선사항
- ESLint 오류 45개 → 12개 (73% 감소)
- 테스트 커버리지 88% → 92% (+4%)
- 번들 크기 2.3MB → 1.8MB (22% 감소)

### ⚠️ 주의사항
- /src/api/auth.js 복잡도 증가 (15 → 18)
- 3개의 의존성 보안 업데이트 필요
- 데이터베이스 쿼리 성능 저하 감지

### 🎯 다음 주 목표
- 복잡도 15 이하로 리팩토링
- 모든 보안 업데이트 적용
- 쿼리 최적화 수행
```

## 🔧 통합 명령어 활용

### 품질 개선 워크플로우
```bash
# 전체 품질 점검
quality/code-analyzer → clean → test → review

# 보안 강화
quality/security-scanner → fix-issue → test → commit

# 성능 최적화
automation/optimizer → test → benchmark → deploy
```

## 🤝 다른 에이전트와의 협업

### Command Executor와 연동
```python
def collaborate_with_executor():
    if quality_score < 80:
        # Command Executor에게 품질 개선 요청
        request_execution([
            "clean --deep",
            "fix-issue --quality",
            "test --comprehensive"
        ])
```

### Workflow Agent와 연동
```python
def integrate_with_workflow():
    # 모든 PR 전 품질 검증
    pre_pr_checks = [
        "lint_check",
        "test_coverage",
        "security_scan"
    ]
    return all_checks_pass(pre_pr_checks)
```

## 📈 지속적 개선

### 학습 및 적응
1. **패턴 인식**: 반복되는 문제 유형 학습
2. **사전 예방**: 문제 발생 전 경고
3. **최적화 제안**: 프로젝트별 맞춤 규칙
4. **자동화 확대**: 수동 작업 점진적 자동화

## 🎯 목표

> "개발자가 비즈니스 로직에만 집중할 수 있도록,
> 모든 품질 관련 작업을 자동화하고 지속적으로 개선한다."

이 에이전트는 24/7 프로젝트를 감시하며, 품질 저하를 사전에 방지하고,
발견된 문제를 즉시 해결하여 항상 최상의 코드 품질을 유지합니다.