# 최적화된 개발 워크플로우 (2025년 초기화)

## 일상적 개발 패턴

### 빠른 시작 시퀀스
```bash
# 1. 환경 초기화 (최초 1회)
make init                           # 의존성 + DB + .env 설정
cp .env.example .env && nano .env   # 크리덴셜 구성

# 2. 일반 개발 시작
make start                          # Docker 환경 (포트 32542)
# 또는
make dev                           # 로컬 환경 (포트 8541, 핫 리로드)
```

### 코드 품질 워크플로우
```bash
# 개발 중 실행 (빠른 피드백)
pytest -m "not slow" -v            # 빠른 테스트만
make lint                          # 기본 코드 품질 체크

# 커밋 전 실행 (완전 검증)
make test                          # 전체 테스트 + 커버리지
make security                      # 보안 검사 (bandit + safety)
black src/ tests/ && isort src/ tests/  # 코드 포맷팅
```

### 성능 최적화 체크리스트
```python
# 1. JSON 처리 - orjson 사용 확인
import orjson
response = orjson.dumps(data)

# 2. 캐시 사용 - TTL 설정 필수
@cached(cache, ttl=300, key_prefix="api_")

# 3. DB 쿼리 - N+1 방지
query.options(joinedload(Model.relationship))

# 4. 대용량 응답 - 압축 활성화
app.config['COMPRESS_MIMETYPES'].append('application/json')
```

## MSA 전환 패턴

### 서비스 분리 기준
- **API Gateway**: 라우팅, 인증, 레이트 리미팅
- **Collection Service**: 외부 데이터 수집 (REGTECH/SECUDIUM)  
- **Blacklist Service**: IP 관리, FortiGate 연동
- **Analytics Service**: 통계, 트렌드 분석

### 서비스간 통신 최적화
```python
# HTTP/2 연결 재사용
session = requests.Session()
session.keep_alive = True

# 비동기 처리
import asyncio, aiohttp
async def fetch_service_data():
    async with aiohttp.ClientSession() as session:
        # 병렬 요청
```

## GitOps 배포 패턴

### 배포 성공률 개선 (현재 60% → 목표 95%)
```bash
# 1. 사전 검증
make lint && make test              # 로컬 완전 검증
docker build -t test-image .        # 빌드 테스트
docker run --rm test-image pytest   # 컨테이너 내 테스트

# 2. 배포 실행
make deploy                         # 전체 GitOps 파이프라인
# 내부적으로: build → push → argocd-sync

# 3. 배포 검증
kubectl get pods -n blacklist      # 파드 상태 확인  
curl http://blacklist.jclee.me/health | jq  # 헬스체크

# 4. 롤백 (필요시)
kubectl rollout undo deployment/blacklist -n blacklist
```

### ArgoCD 이슈 해결 패턴
```bash
# OutOfSync 해결
argocd app sync blacklist --force --timeout 300

# 파드 Pending 해결
kubectl describe pod <pending-pod> -n blacklist
kubectl get nodes --show-labels

# 502 에러 해결
kubectl logs -f deployment/blacklist -n blacklist --tail=100
```

## 테스트 전략 최적화

### 개발 속도 우선 (TDD)
```bash
# 빠른 단위 테스트
pytest -m unit -v                  # <1초 목표

# 특정 기능 집중 테스트  
pytest -k "collection" -v          # 컬렉션 관련만
pytest tests/test_apis.py::test_regtech_apis -v  # 단일 함수
```

### 통합 검증 (CI/CD)
```bash
# 전체 테스트 매트릭스
pytest -m integration --cov=src --cov-report=html
pytest -m api -v                   # API 엔드포인트
pytest -m "slow" -v                # 실제 외부 API 호출
```

## 성능 모니터링 자동화

### 기준선 추적
```bash
# 성능 벤치마크 (자동 실행)
python3 tests/integration/performance_benchmark.py

# API 응답시간 모니터링
curl -w "Time: %{time_total}s\n" http://localhost:32542/api/blacklist/active

# 목표: 7.58ms → 5ms 달성
```

### 병목 지점 프로파일링
```python
# 프로파일러 활성화 (개발 중)
from flask_profiler import Profiler
profiler = Profiler()
profiler.init_app(app)

# 메모리 사용량 추적
import psutil
process = psutil.Process()
memory_mb = process.memory_info().rss / 1024 / 1024
```

## 보안 및 운영 체크리스트

### 환경별 설정 확인
```bash
# 개발 환경 (.env.example)
FORCE_DISABLE_COLLECTION=true      # 안전 모드

# 프로덕션 환경 (docker-compose.yml)
FORCE_DISABLE_COLLECTION=false     # 컬렉션 활성화
COLLECTION_ENABLED=true
```

### 정기 보안 점검
```bash
# 주간 실행
bandit -r src/ -ll                  # 보안 취약점
safety check                       # 의존성 취약점
docker scan registry.jclee.me/blacklist:latest  # 이미지 스캔
```

이 워크플로우는 실제 사용 패턴을 기반으로 최적화되었으며, 개발 효율성과 품질을 균형있게 고려합니다.