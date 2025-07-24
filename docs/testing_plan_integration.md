# 전체 모듈 Rust-style 인라인 통합 테스트 계획

## 테스트 아키텍처 개요

본 계획은 전체 코드베이스에 대해 Rust 스타일의 인라인 통합 테스트를 구현합니다.
각 모듈 파일 끝에 테스트 함수를 추가하여 즉시 검증 가능한 테스트 체계를 구축합니다.

### 테스트 원칙
1. **실제 데이터 사용**: Mock 금지, 9,521개 실제 IP 데이터 활용
2. **모듈별 독립성**: 각 모듈은 독립적으로 테스트 가능
3. **인라인 테스트**: 파일 끝에 `if __name__ == "__main__":` 블록 활용
4. **즉시 검증**: 모듈 실행시 즉시 테스트 결과 확인

## 1. 핵심 서비스 모듈 (Core Services)

### 1.1 Dependency Injection Container (`src/core/container.py`)

현재 상태: 컨테이너 구현되어 있으나 테스트 없음

**테스트 케이스:**
```python
def _test_container_service_registration():
    """서비스 등록 및 해결 테스트"""
    container = BlacklistContainer()
    container.initialize()
    
    # 핵심 서비스들 검증
    assert container.resolve('blacklist_manager') is not None
    assert container.resolve('cache_manager') is not None
    assert container.resolve('auth_manager') is not None
    print("✅ Container 서비스 등록/해결 테스트 통과")

def _test_container_singleton_behavior():
    """싱글톤 동작 검증"""
    container = get_container()
    manager1 = container.resolve('blacklist_manager')
    manager2 = container.resolve('blacklist_manager')
    assert manager1 is manager2
    print("✅ Container 싱글톤 동작 테스트 통과")

def _test_container_dependency_injection():
    """의존성 주입 검증"""
    container = get_container()
    service_info = container.get_service_info()
    
    # 필수 서비스들이 등록되어 있는지 확인
    required_services = ['blacklist_manager', 'cache_manager', 'auth_manager']
    for service in required_services:
        assert service in service_info
        assert service_info[service]['instantiated']
    print("✅ Container 의존성 주입 테스트 통과")
```

### 1.2 통합 블랙리스트 매니저 (`src/core/blacklist_unified.py`)

현재 상태: 핵심 비즈니스 로직, 테스트 필요

**테스트 케이스:**
```python
def _test_blacklist_manager_basic_operations():
    """기본 블랙리스트 작업 테스트"""
    from src.core.container import get_container
    
    container = get_container()
    manager = container.resolve('blacklist_manager')
    
    # 현재 IP 수 확인 (9,521개 예상)
    active_ips = manager.get_active_blacklist()
    assert len(active_ips) > 9000
    print(f"✅ 활성 IP 수: {len(active_ips)}")

def _test_blacklist_manager_fortigate_format():
    """FortiGate 형식 변환 테스트"""
    container = get_container()
    manager = container.resolve('blacklist_manager')
    
    fortigate_data = manager.get_fortigate_external_connector()
    assert isinstance(fortigate_data, dict)
    assert 'results' in fortigate_data
    assert len(fortigate_data['results']) > 0
    print(f"✅ FortiGate 형식 변환: {len(fortigate_data['results'])}개 항목")

def _test_blacklist_manager_statistics():
    """통계 생성 테스트"""
    container = get_container()
    manager = container.resolve('blacklist_manager')
    
    stats = manager.get_statistics()
    assert stats['total_ips'] > 0
    assert 'last_updated' in stats
    print(f"✅ 통계 생성: {stats['total_ips']}개 IP")
```

### 1.3 통합 서비스 (`src/core/unified_service.py`)

현재 상태: 서비스 오케스트레이터, 컬렉션 로깅 포함

**테스트 케이스:**
```python
def _test_unified_service_initialization():
    """통합 서비스 초기화 테스트"""
    from .unified_service import UnifiedBlacklistService
    
    service = UnifiedBlacklistService()
    assert service.container is not None
    assert service.blacklist_manager is not None
    print("✅ 통합 서비스 초기화 성공")

def _test_unified_service_collection_logging():
    """컬렉션 로깅 시스템 테스트"""
    service = UnifiedBlacklistService()
    
    # 테스트 로그 추가
    service.add_collection_log('TEST', 'validation', {'ips_processed': 100})
    
    logs = service.get_recent_collection_logs()
    assert len(logs) > 0
    assert logs[0]['source'] == 'TEST'
    print("✅ 컬렉션 로깅 시스템 동작 확인")

def _test_unified_service_statistics():
    """통합 서비스 통계 테스트"""
    service = UnifiedBlacklistService()
    
    stats = service.get_enhanced_statistics()
    assert 'total_ips' in stats
    assert stats['total_ips'] > 0
    print(f"✅ 통합 서비스 통계: {stats['total_ips']}개 IP")
```

## 2. 데이터 수집기 모듈 (Collectors)

### 2.1 REGTECH 수집기 (`src/core/regtech_simple_collector.py`)

현재 상태: 간단한 수집기, 인증 이슈 존재

**테스트 케이스:**
```python
def _test_regtech_collector_initialization():
    """REGTECH 수집기 초기화 테스트"""
    from .regtech_simple_collector import RegtechSimpleCollector
    
    collector = RegtechSimpleCollector('data')
    assert collector.data_path == 'data'
    print("✅ REGTECH 수집기 초기화 성공")

def _test_regtech_collector_authentication():
    """REGTECH 인증 테스트 (외부 의존성)"""
    collector = RegtechSimpleCollector('data')
    
    try:
        # 실제 인증 시도 (실패 예상)
        result = collector.collect_from_web()
        if result and len(result) > 0:
            print(f"✅ REGTECH 인증 성공: {len(result)}개 IP 수집")
        else:
            print("⚠️ REGTECH 인증 실패 (예상됨)")
    except Exception as e:
        print(f"⚠️ REGTECH 인증 실패: {str(e)[:50]}...")

def _test_regtech_collector_file_operations():
    """REGTECH 파일 작업 테스트"""
    import os
    collector = RegtechSimpleCollector('data')
    
    # 데이터 디렉토리 확인
    if os.path.exists('data'):
        print("✅ 데이터 디렉토리 존재")
    else:
        print("⚠️ 데이터 디렉토리 없음")
```

### 2.2 SECUDIUM 수집기 (`src/core/secudium_collector.py`)

현재 상태: POST 기반 로그인, Excel 다운로드

**테스트 케이스:**
```python
def _test_secudium_collector_initialization():
    """SECUDIUM 수집기 초기화 테스트"""
    from .secudium_collector import SecudiumCollector
    
    collector = SecudiumCollector('data')
    assert collector.data_path == 'data'
    print("✅ SECUDIUM 수집기 초기화 성공")

def _test_secudium_collector_authentication():
    """SECUDIUM 인증 테스트 (외부 의존성)"""
    collector = SecudiumCollector('data')
    
    try:
        result = collector.collect_from_web()
        if result and len(result) > 0:
            print(f"✅ SECUDIUM 인증 성공: {len(result)}개 IP 수집")
        else:
            print("⚠️ SECUDIUM 인증 실패 (예상됨)")
    except Exception as e:
        print(f"⚠️ SECUDIUM 인증 실패: {str(e)[:50]}...")

def _test_secudium_excel_processing():
    """SECUDIUM Excel 처리 로직 테스트"""
    collector = SecudiumCollector('data')
    
    # Excel 처리 함수가 존재하는지 확인
    assert hasattr(collector, 'extract_ips_from_excel')
    print("✅ SECUDIUM Excel 처리 함수 존재")
```

### 2.3 컬렉션 매니저 (`src/core/collection_manager.py`)

현재 상태: 중앙 집중식 컬렉션 관리

**테스트 케이스:**
```python
def _test_collection_manager_initialization():
    """컬렉션 매니저 초기화 테스트"""
    from .collection_manager import CollectionManager
    
    manager = CollectionManager()
    assert manager is not None
    print("✅ 컬렉션 매니저 초기화 성공")

def _test_collection_manager_status():
    """컬렉션 상태 관리 테스트"""
    manager = CollectionManager()
    
    status = manager.get_collection_status()
    assert isinstance(status, dict)
    assert 'enabled' in status
    print(f"✅ 컬렉션 상태: {status}")

def _test_collection_manager_enable_disable():
    """컬렉션 활성화/비활성화 테스트"""
    manager = CollectionManager()
    
    # 비활성화
    manager.disable_collection()
    status_disabled = manager.get_collection_status()
    assert not status_disabled['enabled']
    
    # 활성화
    manager.enable_collection()
    status_enabled = manager.get_collection_status()
    assert status_enabled['enabled']
    
    print("✅ 컬렉션 활성화/비활성화 동작 확인")
```

## 3. 캐시 시스템 (`src/utils/advanced_cache.py`)

현재 상태: Redis/메모리 이중화 캐시

**테스트 케이스:**
```python
def _test_cache_basic_operations():
    """캐시 기본 작업 테스트"""
    from .advanced_cache import AdvancedCache
    
    cache = AdvancedCache()
    
    # 기본 설정/조회 테스트
    cache.set('test_key', 'test_value', ttl=60)
    value = cache.get('test_key')
    assert value == 'test_value'
    print("✅ 캐시 기본 작업 성공")

def _test_cache_redis_fallback():
    """Redis 실패시 메모리 캐시 폴백 테스트"""
    cache = AdvancedCache()
    
    # Redis 연결 상태 확인
    redis_available = cache._test_redis_connection()
    print(f"✅ Redis 연결 상태: {'사용 가능' if redis_available else '메모리 폴백'}")

def _test_cache_performance():
    """캐시 성능 테스트"""
    import time
    cache = AdvancedCache()
    
    # 성능 측정
    start_time = time.time()
    for i in range(100):
        cache.set(f'perf_key_{i}', f'value_{i}', ttl=60)
        cache.get(f'perf_key_{i}')
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"✅ 캐시 성능: 200회 작업 {duration:.3f}초")
```

## 4. API 엔드포인트 (`src/core/unified_routes.py`)

현재 상태: 일부 인라인 테스트 존재, 확장 필요

**확장할 테스트 케이스:**
```python
def _test_enhanced_api_endpoints():
    """향상된 API 엔드포인트 테스트"""
    from flask import Flask
    from . import create_test_app
    
    app = create_test_app()
    
    with app.test_client() as client:
        # V2 API 테스트
        response = client.get('/api/v2/blacklist/enhanced')
        assert response.status_code == 200
        
        # 분석 API 테스트
        response = client.get('/api/v2/analytics/trends')
        assert response.status_code == 200
        
        print("✅ 향상된 API 엔드포인트 테스트 통과")

def _test_api_error_handling():
    """API 오류 처리 테스트"""
    app = create_test_app()
    
    with app.test_client() as client:
        # 존재하지 않는 엔드포인트
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        
        # 잘못된 메소드
        response = client.post('/api/stats')
        assert response.status_code == 405
        
        print("✅ API 오류 처리 테스트 통과")

def _test_api_response_format():
    """API 응답 형식 테스트"""
    app = create_test_app()
    
    with app.test_client() as client:
        response = client.get('/api/stats')
        data = response.get_json()
        
        # 필수 필드 확인
        required_fields = ['total_ips', 'last_updated', 'sources']
        for field in required_fields:
            assert field in data
        
        print("✅ API 응답 형식 테스트 통과")
```

## 5. 유틸리티 모듈

### 5.1 인증 관리자 (`src/utils/auth.py`)

**테스트 케이스:**
```python
def _test_auth_manager_initialization():
    """인증 관리자 초기화 테스트"""
    from .auth import AuthManager
    
    auth_manager = AuthManager()
    assert auth_manager is not None
    print("✅ 인증 관리자 초기화 성공")

def _test_auth_token_operations():
    """토큰 작업 테스트"""
    auth_manager = AuthManager()
    
    # 토큰 생성
    token = auth_manager.generate_token({'user_id': 'test'})
    assert token is not None
    
    # 토큰 검증
    payload = auth_manager.verify_token(token)
    assert payload['user_id'] == 'test'
    
    print("✅ 토큰 생성/검증 테스트 통과")
```

### 5.2 모니터링 (`src/utils/monitoring.py`)

**테스트 케이스:**
```python
def _test_monitoring_metrics():
    """모니터링 메트릭 테스트"""
    from .monitoring import get_metrics_collector
    
    metrics = get_metrics_collector()
    
    # 메트릭 수집
    system_info = metrics.collect_system_metrics()
    assert 'cpu_usage' in system_info
    assert 'memory_usage' in system_info
    
    print("✅ 시스템 메트릭 수집 성공")

def _test_health_checker():
    """헬스 체커 테스트"""
    from .monitoring import get_health_checker
    
    health_checker = get_health_checker()
    
    # 헬스 체크 실행
    health_status = health_checker.check_system_health()
    assert 'status' in health_status
    
    print("✅ 헬스 체크 시스템 동작 확인")
```

## 6. 설정 관리 (`src/config/`)

### 6.1 팩토리 (`src/config/factory.py`)

**테스트 케이스:**
```python
def _test_config_factory():
    """설정 팩토리 테스트"""
    from .factory import get_config
    
    config = get_config()
    assert config is not None
    assert hasattr(config, 'SECRET_KEY')
    
    print("✅ 설정 팩토리 동작 확인")

def _test_config_environment_detection():
    """환경 감지 테스트"""
    import os
    
    # 현재 환경 확인
    env = os.getenv('FLASK_ENV', 'development')
    print(f"✅ 현재 환경: {env}")
```

## 7. 데이터베이스 (`src/core/database.py`)

**테스트 케이스:**
```python
def _test_database_connection():
    """데이터베이스 연결 테스트"""
    from .database import DatabaseManager
    from ..config.settings import settings
    
    db_manager = DatabaseManager(settings.database_uri)
    
    # 연결 테스트
    connection_ok = db_manager.test_connection()
    assert connection_ok
    
    print("✅ 데이터베이스 연결 성공")

def _test_database_operations():
    """데이터베이스 기본 작업 테스트"""
    db_manager = DatabaseManager(settings.database_uri)
    
    # IP 수 확인
    ip_count = db_manager.get_total_ip_count()
    assert ip_count > 0
    
    print(f"✅ 데이터베이스 IP 수: {ip_count}")
```

## 8. 메인 애플리케이션 (`src/core/app_compact.py`)

**테스트 케이스:**
```python
def _test_app_creation():
    """애플리케이션 생성 테스트"""
    from .app_compact import create_app
    
    app = create_app()
    assert app is not None
    assert app.config is not None
    
    print("✅ 애플리케이션 생성 성공")

def _test_app_services_injection():
    """애플리케이션 서비스 주입 테스트"""
    app = create_app()
    
    # 필수 서비스들이 주입되었는지 확인
    assert hasattr(app, 'container')
    assert hasattr(app, 'blacklist_manager')
    assert hasattr(app, 'cache')
    
    print("✅ 애플리케이션 서비스 주입 확인")
```

## 실행 계획

### 단계 1: 우선순위 모듈 테스트 구현
1. `src/core/container.py` - 의존성 주입 핵심
2. `src/core/blacklist_unified.py` - 비즈니스 로직 핵심
3. `src/core/unified_service.py` - 서비스 오케스트레이터

### 단계 2: 데이터 수집 모듈 테스트
1. `src/core/collection_manager.py`
2. `src/core/regtech_simple_collector.py`
3. `src/core/secudium_collector.py`

### 단계 3: 인프라 모듈 테스트
1. `src/utils/advanced_cache.py`
2. `src/utils/auth.py`
3. `src/utils/monitoring.py`

### 단계 4: API 및 애플리케이션 테스트
1. `src/core/unified_routes.py` (기존 확장)
2. `src/core/app_compact.py`
3. `src/config/factory.py`

## 테스트 실행 방법

각 모듈별 개별 실행:
```bash
python3 src/core/container.py
python3 src/core/blacklist_unified.py
python3 src/utils/advanced_cache.py
```

전체 테스트 실행:
```bash
python3 scripts/run_all_inline_tests.py
```

## 기대 결과

- 각 모듈이 독립적으로 검증 가능
- 실제 데이터(9,521개 IP)를 사용한 현실적 테스트
- 즉시 피드백으로 개발 속도 향상
- 리팩토링시 안전성 보장
- 코드 품질 향상 및 버그 조기 발견