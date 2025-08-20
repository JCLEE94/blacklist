# Blacklist 프로젝트 개발 패턴 및 워크플로우

## 핵심 개발 패턴

### 1. 자동화된 CI/CD 워크플로우
```bash
# 완전 자동화된 배포 프로세스
git add . && git commit -m "feat: 새로운 기능"
git push origin main  # 이것만으로 모든 배포 완료!

# 자동으로 실행되는 작업:
# 1. 버전 자동 생성: YYYYMMDD-HHMMSS-GITHASH
# 2. Docker 이미지 빌드 및 푸시
# 3. Helm Chart 자동 업데이트  
# 4. ArgoCD 동기화 (3분 내)
# 5. GitHub Pages 포트폴리오 업데이트
```

### 2. 서비스 아키텍처 패턴
```python
# 의존성 주입 패턴
from src.core.container import get_container
container = get_container()
service = container.get('unified_service')

# 캐시 사용 패턴 (중요: ttl= 사용, timeout= 아님)
cache.set(key, value, ttl=300)
@cached(cache, ttl=300, key_prefix="stats")

# 서비스 팩토리 패턴
from src.core.services.unified_service_factory import get_unified_service
service = get_unified_service()
```

### 3. 테스트 실행 패턴
```bash
# 마커 기반 테스트 실행
pytest -m "not slow" -v           # 빠른 테스트만
pytest -m "unit" -v               # 단위 테스트
pytest -m "integration" -v        # 통합 테스트
pytest -m "api" -v                # API 테스트

# 커버리지 포함 전체 테스트
make test  # = pytest --cov=src --cov-report=html
```

## 자주 사용되는 명령어

### 개발 환경
```bash
# 환경 초기화 (한 번만 실행)
make init

# 서비스 시작/중지
make start    # Docker Compose 시작 (포트 32542)
make stop     # 서비스 중지
make status   # 상태 확인
make logs     # 로그 확인

# 로컬 개발
python3 main.py --debug  # 디버그 모드 (포트 8541)
make dev                  # 자동 리로드 모드
```

### 배포 및 운영
```bash
# 헬스체크
curl http://localhost:32542/health | jq       # Docker 환경
curl http://localhost:8541/health | jq        # 로컬 환경

# 수집 시스템 제어
curl -X POST http://localhost:32542/api/collection/enable
curl -X POST http://localhost:32542/api/collection/disable
curl http://localhost:32542/api/collection/status | jq

# ArgoCD 수동 동기화 (필요시)
curl -X POST -H "Authorization: Bearer $ARGOCD_TOKEN" \
  http://192.168.50.110:31017/api/v1/applications/blacklist/sync
```

## 코딩 스타일 및 컨벤션

### 파일 크기 제한
- **500라인 엄격 제한**: 모든 Python 파일
- 초과시 믹스인 또는 모듈로 분할
- 블루프린트 패턴으로 라우트 분산

### 에러 처리 패턴
```python
# 절대 크래시하지 않는 패턴
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return fallback_value
```

### 보안 우선 설정
```python
# 기본값: 외부 인증 차단
FORCE_DISABLE_COLLECTION=true    # 안전한 기본값
COLLECTION_ENABLED=false         # 프로덕션에서만 활성화

# Docker: 프로덕션 설정
FORCE_DISABLE_COLLECTION=false   # 수집 허용
COLLECTION_ENABLED=true          # 활성 수집
```

## 성능 최적화 패턴

### 병렬 실행
- CI/CD 파이프라인: GitOps + Pages 병렬 실행 (60% 시간 절약)
- 테스트 실행: 마커 기반 선택적 실행
- 서비스 시작: Docker Compose 동시 시작

### 캐싱 전략
- Redis 주 캐시 + 메모리 폴백
- API 응답 캐시 (TTL 300초)
- 통계 데이터 캐시 최적화

## 문제 해결 패턴

### ImagePullBackOff
```bash
# 이미지 태그 확인
kubectl describe pod blacklist-xxx -n blacklist

# 레지스트리 로그인 상태 확인
docker login registry.jclee.me -u admin
echo "bingogo1" | docker login registry.jclee.me -u admin --password-stdin
```

### ArgoCD 동기화 실패
```bash
# 앱 상태 확인
curl -H "Authorization: Bearer $ARGOCD_TOKEN" \
  http://192.168.50.110:31017/api/v1/applications/blacklist

# 수동 동기화
curl -X POST -H "Authorization: Bearer $ARGOCD_TOKEN" \
  http://192.168.50.110:31017/api/v1/applications/blacklist/sync
```

### 포트 충돌
```bash
# Docker 환경: 32542
lsof -i :32542 || netstat -tunlp | grep 32542

# 로컬 환경: 8541  
lsof -i :8541 || netstat -tunlp | grep 8541
```