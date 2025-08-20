# 팀 컨벤션 및 패턴 (2025년 정립)

## 코드 작성 규칙

### 파일 크기 제한 (엄격 준수)
- **최대 500라인** 파이썬 파일
- 초과시 모듈 분할 필수
- 믹스인 패턴으로 기능 조합
- 블루프린트로 라우트 분리

### 네이밍 컨벤션
```python
# 함수/변수: snake_case  
def get_blacklist_data():
    collection_status = True
    
# 클래스: PascalCase
class UnifiedServiceCore:
    class CollectionServiceMixin:
        pass

# 상수: UPPER_CASE
CACHE_PREFIX_STATS = "stats:"
DATABASE_POOL_SIZE = 20

# 컨테이너 서비스: snake_case
container.get('unified_service')
container.get('blacklist_manager')
```

### 타입 힌트 전략
```python
from typing import Dict, List, Optional, Union, TypeVar
from src.core.models import BlacklistEntry, CollectionStatus

# 제네릭 타입 정의
T = TypeVar('T')

def process_blacklist_data(
    entries: List[BlacklistEntry],
    cache_ttl: Optional[int] = 300
) -> Dict[str, Union[str, int]]:
    """명확한 타입 힌트로 API 계약 정의"""
    pass
```

## 에러 처리 철학

### Never Crash 원칙
```python
# ✅ 권장: 항상 폴백 제공
try:
    result = external_api_call()
except Exception as e:
    logger.error(f"External API failed: {e}")
    result = get_cached_fallback()  # 캐시된 데이터로 폴백
    
# ❌ 금지: 예외 전파로 서비스 중단
result = external_api_call()  # 예외 처리 없음
```

### 로깅 전략
```python
import logging
logger = logging.getLogger(__name__)

# 에러 발생 시 충분한 컨텍스트 제공
try:
    process_collection_data(source='REGTECH')
except CollectionError as e:
    logger.error(f"Collection failed - source: REGTECH, reason: {e}, "
                f"retry_count: {retry_count}, timestamp: {datetime.now()}")
    # 폴백 로직
```

## 의존성 주입 패턴

### 컨테이너 기반 서비스 관리
```python
# 권장: 컨테이너를 통한 서비스 접근
from src.core.container import get_container
container = get_container()
service = container.get('unified_service')

# 대안: 팩토리 패턴 (싱글톤)
from src.core.services.unified_service_factory import get_unified_service
service = get_unified_service()

# ❌ 금지: 직접 인스턴스 생성
service = UnifiedService()  # 싱글톤 깨짐
```

### 서비스 등록 패턴
```python
# BlacklistContainer에서 중앙 관리
container.register('cache_manager', lambda: CacheManager(redis_client))
container.register('blacklist_manager', lambda: BlacklistManager(db))
```

## 캐싱 전략

### Redis 기본 + 메모리 폴백
```python
# ✅ 권장: ttl 파라미터 사용
cache.set(key, value, ttl=300)
@cached(cache, ttl=300, key_prefix="api_")

# ❌ 금지: timeout 파라미터 (레거시)
cache.set(key, value, timeout=300)  # 동작하지 않음
```

### 캐시 키 명명 규칙
```python
# 접두사 기반 구조화
CACHE_PREFIX_STATS = "stats:"
CACHE_PREFIX_BLACKLIST = "bl:"
CACHE_PREFIX_COLLECTION = "coll:"

# 예시: "stats:daily:2025-01-11:regtech"
cache_key = f"{CACHE_PREFIX_STATS}daily:{date}:{source}"
```

## 데이터베이스 최적화

### N+1 쿼리 방지
```python
# ✅ 권장: Eager Loading
blacklist_entries = session.query(BlacklistEntry).options(
    joinedload(BlacklistEntry.source),
    joinedload(BlacklistEntry.detection_info)
).all()

# ❌ 금지: Lazy Loading (N+1 발생)
for entry in blacklist_entries:
    source_name = entry.source.name  # 매번 DB 조회
```

### 배치 처리
```python
# 대량 데이터 배치 삽입
session.bulk_insert_mappings(BlacklistEntry, entries_data)
session.commit()

# 스트리밍 처리 (메모리 효율)
def process_large_dataset(query):
    for batch in query.yield_per(1000):
        process_batch(batch)
```

## API 설계 원칙

### 요청 데이터 처리 표준화
```python
# JSON과 폼 데이터 모두 지원
if request.is_json:
    data = request.get_json() or {}
else:
    data = request.form.to_dict() or {}

# 기본값 처리
start_date = data.get('start_date', default_start_date)
```

### 응답 형식 일관성
```python
# 성공 응답
{
    "success": true,
    "data": {...},
    "meta": {"count": 150, "timestamp": "2025-01-11T10:30:00Z"}
}

# 에러 응답  
{
    "success": false,
    "error": {"code": "COLLECTION_FAILED", "message": "상세 에러 메시지"},
    "meta": {"request_id": "uuid"}
}
```

## 비동기 처리 가이드라인

### 컬렉션 시스템 비동기화
```python
import asyncio
import aiohttp

# 병렬 소스 수집
async def collect_all_sources():
    tasks = [
        collect_regtech_async(),
        collect_secudium_async()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return process_results(results)
```

## 테스트 작성 규칙

### 테스트 마커 활용
```python
import pytest

# 빠른 단위 테스트
@pytest.mark.unit
def test_ip_validation():
    pass

# 느린 통합 테스트  
@pytest.mark.slow
@pytest.mark.integration
def test_full_collection_workflow():
    pass

# 소스별 테스트
@pytest.mark.regtech
def test_regtech_authentication():
    pass
```

### 테스트 데이터 관리
```python
# 픽스처 활용
@pytest.fixture
def sample_blacklist_data():
    return [
        {'ip': '192.168.1.1', 'source': 'REGTECH', 'threat_level': 'HIGH'},
        {'ip': '10.0.0.1', 'source': 'SECUDIUM', 'threat_level': 'MEDIUM'}
    ]
```

## 한영 혼용 문서화

### 비즈니스 로직: 한국어
```python
def 위협_IP_차단_해제(ip_address: str):
    """
    특정 IP의 차단을 해제합니다.
    FortiGate 연동을 통해 실시간 반영됩니다.
    """
    pass
```

### 기술 구현: 영어
```python
class CacheManager:
    """Handles Redis caching with memory fallback strategy."""
    
    def get_cached_data(self, key: str) -> Optional[Dict]:
        """Retrieve data from cache with fallback logic."""
        pass
```

이러한 컨벤션을 통해 코드 일관성과 유지보수성을 높이며, 한국 기업 환경에 적합한 개발 문화를 구축합니다.