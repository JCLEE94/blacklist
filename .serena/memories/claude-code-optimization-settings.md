# Claude Code 환경 최적화 설정

## 1. 에이전트 구성 최적화

### 프로젝트별 전문 에이전트 설정
```yaml
# 권장 에이전트 사용 패턴
analyzer-project-state:     # 프로젝트 상태 분석 (정기적)
cleaner-code-quality:       # 코드 정리 및 ESLint (주간)  
runner-test-automation:     # 테스트 실행 및 커버리지 (일일)
specialist-deployment-infra: # Docker/K8s/ArgoCD 배포 (필요시)
general-purpose:            # 복합 작업 및 연구 (상시)
```

### 에이전트별 최적 사용 시나리오
- **analyzer-project-state**: 프로젝트 시작시, 주요 변경 후
- **cleaner-code-quality**: 코드 리팩토링, 스타일 정리시
- **runner-test-automation**: CI/CD 전, 배포 전 검증
- **specialist-deployment-infra**: 인프라 변경, 배포 이슈
- **general-purpose**: 복잡한 멀티스텝 작업

## 2. 성능 최적화 설정

### 병렬 실행 최적화
```yaml
# CI/CD 파이프라인 병렬화
concurrency:
  group: "unified-pipeline"
  cancel-in-progress: false

# 작업별 병렬 실행
jobs:
  gitops-deploy:     # GitOps 배포 (self-hosted)
  pages-deploy:      # 포트폴리오 배포 (ubuntu-latest)
  # 두 작업이 동시 실행되어 60% 시간 절약
```

### 캐싱 전략 최적화
```python
# Redis 캐시 + 메모리 폴백
REDIS_URL=redis://redis:6379/0
CACHE_TIMEOUT=300  # 5분 TTL

# API 응답 캐시
@cached(cache, ttl=300, key_prefix="api")
def get_blacklist_data():
    return heavy_computation()

# 통계 데이터 캐시  
@cached(cache, ttl=600, key_prefix="stats")
def get_statistics():
    return analytics_computation()
```

## 3. 도구 통합 최적화

### MCP 도구 설정
```yaml
# ESLint 설정 (JavaScript 파일용)
eslint:
  rules: "src/**/*.js"
  config: ".eslintrc.json"
  
# pytest 설정 (Python 테스트)
pytest:
  config: "pytest.ini" 
  markers: "unit,integration,api,performance"
  coverage: "--cov=src --cov-report=html"

# Git hooks 설정
pre-commit:
  - black src/ tests/      # 코드 포맷팅
  - isort src/ tests/      # import 정렬
  - flake8 src/           # 린팅
```

### 자동화 스크립트 최적화
```bash
# Makefile 기반 자동화
make init     # 환경 초기화 (한 번)
make start    # 서비스 시작
make test     # 테스트 실행 + 커버리지
make deploy   # 전체 배포 파이프라인

# 스마트 스크립트 감지
./start.sh    # Docker Compose 관리
scripts/auto-deploy-test.sh  # 배포 테스트
scripts/load-env.sh          # 환경변수 로드
```

## 4. 진행 상황 추적 최적화

### TodoWrite 사용 패턴
```python
# 복잡한 멀티스텝 작업시 필수 사용
# 3단계 이상 작업에서 프로액티브하게 활용
# 실시간 상태 업데이트로 사용자 가시성 확보

# 권장 사용 시점:
# - 프로젝트 초기화
# - 새로운 기능 개발  
# - 배포 및 인프라 작업
# - 버그 수정 및 최적화
```

### 메모리 관리 최적화
```python
# 프로젝트별 패턴 저장
mcp__serena__write_memory("project-patterns", content)

# 자주 참조되는 명령어 저장  
mcp__serena__write_memory("common-commands", commands)

# 문제 해결 절차 저장
mcp__serena__write_memory("troubleshooting-guide", procedures)
```

## 5. 타임아웃 및 리소스 최적화

### 적절한 타임아웃 설정
```yaml
# CI/CD 파이프라인 타임아웃
GitOps Deploy: 10분     # Docker 빌드 + 푸시 + 배포
Pages Deploy: 5분       # 정적 사이트 생성 + 배포
ArgoCD Sync: 3분        # 자동 동기화 대기시간

# API 응답 타임아웃  
Health Check: 5초       # 헬스체크 응답
API Request: 30초       # 일반 API 요청
Collection: 300초       # 데이터 수집 작업
```

### 리소스 할당 최적화
```yaml
# Kubernetes 리소스 제한
blacklist:
  requests: { cpu: 25m, memory: 64Mi }
  limits:   { cpu: 200m, memory: 128Mi }
  
redis:  
  requests: { cpu: 25m, memory: 32Mi }
  limits:   { cpu: 50m, memory: 64Mi }
```

## 6. 모니터링 및 관찰성

### 통합 모니터링 스택
```yaml
# Prometheus + Grafana + ELK
prometheus: "http://localhost:9090"      # 메트릭 수집
grafana:    "http://localhost:3000"      # 대시보드 (admin/admin123)
kibana:     "http://localhost:5601"      # 로그 분석
elasticsearch: "http://localhost:9200"   # 로그 저장

# ArgoCD 모니터링
argocd: "https://argo.jclee.me/applications/blacklist"
```

### 성능 벤치마킹
```bash
# 자동 성능 테스트
python3 tests/integration/performance_benchmark.py

# API 응답시간 측정
curl -X GET "http://localhost:32542/api/blacklist/active" \
  -w "\nTime: %{time_total}s\n"

# 목표 성능 지표
API Response: < 50ms     # 블랙리스트 조회
Health Check: < 5ms      # 헬스체크  
Collection: < 300s       # 데이터 수집
```

## 7. 보안 및 규정 준수

### 기본 보안 설정
```bash
# 안전한 기본값 (로컬 개발)
FORCE_DISABLE_COLLECTION=true
COLLECTION_ENABLED=false
MAX_AUTH_ATTEMPTS=10
BLOCK_DURATION_HOURS=24

# 프로덕션 설정 (Docker)
FORCE_DISABLE_COLLECTION=false
COLLECTION_ENABLED=true  
MAX_AUTH_ATTEMPTS=5
BLOCK_DURATION_HOURS=1
```

### 자동 보안 검사
```bash  
# 의존성 취약점 스캔
safety check

# 코드 보안 분석
bandit -r src/ -ll

# 컨테이너 보안 (non-root 실행)
USER app:1001  # Dockerfile에서 설정
```