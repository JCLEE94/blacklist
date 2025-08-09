"""
시스템 상수 정의

시스템에서 사용하는 모든 상수와 설정값을 중앙에서 관리합니다.
"""

# ============ 버전 정보 ============
API_VERSION = "2.1.0-unified"
SYSTEM_NAME = "Secudium Blacklist Manager"
AUTHOR = "Secudium Team"

# ============ 환경 설정 ============
ENV_PRODUCTION = "production"
ENV_DEVELOPMENT = "development"
ENV_TESTING = "testing"

# ============ 캐시 설정 ============
DEFAULT_CACHE_TTL = 300  # 5분
LONG_CACHE_TTL = 3600  # 1시간
SHORT_CACHE_TTL = 60  # 1분

# 캐시 키 프리픽스
CACHE_PREFIX_BLACKLIST = "blacklist"
CACHE_PREFIX_STATS = "stats"
CACHE_PREFIX_SEARCH = "search"
CACHE_PREFIX_HEALTH = "health"
CACHE_PREFIX_AUTH = "auth"

# ============ 데이터 보관 설정 ============
DEFAULT_DATA_RETENTION_DAYS = 90  # 3개월
MAX_DATA_RETENTION_DAYS = 365  # 1년
MIN_DATA_RETENTION_DAYS = 30  # 1개월

# ============ 지원하는 IP 형식 ============
SUPPORTED_IP_FORMATS = [
    "ipv4",  # IPv4 주소
    "ipv6",  # IPv6 주소
    "cidr_v4",  # IPv4 CIDR 표기법
    "cidr_v6",  # IPv6 CIDR 표기법
]

# IP 주소 정규표현식 패턴
IP_PATTERNS = {
    "ipv4": r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
    "ipv6": r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$",
    "cidr_v4": r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(?:[0-9]|[1-2][0-9]|3[0-2])$",
    "cidr_v6": r"^(?:[0-9a-fA-F]{1,4}:){1,7}:\/(?:[0-9]|[1-9][0-9]|1[0-1][0-9]|12[0-8])$",
}

# ============ API 설정 ============
# Rate Limiting
DEFAULT_RATE_LIMITS = {
    "public": 1000,  # 공개 엔드포인트: 시간당 1000회
    "authenticated": 5000,  # 인증된 사용자: 시간당 5000회
    "admin": 10000,  # 관리자: 시간당 10000회
    "search": 200,  # 검색 엔드포인트: 시간당 200회
    "batch": 50,  # 배치 처리: 시간당 50회
}

# API 응답 크기 제한
MAX_RESPONSE_SIZE_MB = 50
MAX_BATCH_SIZE = 100
MAX_SEARCH_RESULTS = 1000

# ============ 파일 경로 ============
# 데이터 디렉터리 구조
DATA_STRUCTURE = {
    "blacklist": "blacklist",
    "by_detection_month": "blacklist/by_detection_month",
    "all_downloads": "blacklist/all_downloads",
    "logs": "logs",
    "backups": "backups",
}

# 파일명 패턴
FILE_PATTERNS = {
    "ips": "ips.txt",
    "details": "details.json",
    "stats": "stats.json",
    "all_ips": "all_ips.txt",
    "collection_info": "collection_info.json",
}

# ============ 날짜/시간 형식 ============
DATE_FORMATS = {
    "month": "%Y-%m",  # 2025-06
    "iso_datetime": "%Y-%m-%dT%H:%M:%S",  # 2025-06-09T10:30:00
    "iso_date": "%Y-%m-%d",  # 2025-06-09
    "log_format": "%Y-%m-%d %H:%M:%S",  # 2025-06-09 10:30:00
}

# ============ 로깅 설정 ============
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

LOG_FORMATS = {
    "default": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "detailed": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    "json": '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
}

# ============ HTTP 상태 코드 ============
HTTP_STATUS_CODES = {
    # 성공
    "OK": 200,
    "CREATED": 201,
    "ACCEPTED": 202,
    "NO_CONTENT": 204,
    # 클라이언트 오류
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "METHOD_NOT_ALLOWED": 405,
    "CONFLICT": 409,
    "UNPROCESSABLE_ENTITY": 422,
    "TOO_MANY_REQUESTS": 429,
    # 서버 오류
    "INTERNAL_SERVER_ERROR": 500,
    "NOT_IMPLEMENTED": 501,
    "BAD_GATEWAY": 502,
    "SERVICE_UNAVAILABLE": 503,
    "GATEWAY_TIMEOUT": 504,
}

# ============ 보안 설정 ============
# JWT 토큰 설정
JWT_SETTINGS = {
    "algorithm": "HS256",
    "expiry_hours": 24,  # 24시간
    "refresh_expiry_days": 7,  # 7일
    "issuer": "secudium-api",
    "audience": "secudium-clients",
}

# 보안 헤더
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self' https://cdn.jsdelivr.net; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline' 'unsafe-eval'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; font-src 'self' https://cdn.jsdelivr.net data:; img-src 'self' data: https:;",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}

# ============ 시스템 한계값 ============
SYSTEM_LIMITS = {
    "max_concurrent_requests": 1000,
    "max_memory_usage_mb": 2048,  # 2GB
    "max_cpu_usage_percent": 80,
    "max_disk_usage_percent": 90,
    "max_cache_entries": 10000,
    "max_log_file_size_mb": 100,  # 100MB
    "max_backup_files": 30,
}

# ============ 모니터링 설정 ============
HEALTH_CHECK_INTERVALS = {
    "critical": 30,  # 30초 - 중요한 서비스
    "normal": 60,  # 1분 - 일반 서비스
    "background": 300,  # 5분 - 백그라운드 서비스
}

PERFORMANCE_THRESHOLDS = {
    "response_time_ms": {
        "excellent": 50,
        "good": 200,
        "acceptable": 1000,
        "poor": 5000,
    },
    "memory_usage_percent": {"low": 25, "normal": 50, "high": 75, "critical": 90},
    "cpu_usage_percent": {"low": 20, "normal": 50, "high": 80, "critical": 95},
}

# ============ 에러 메시지 ============
ERROR_MESSAGES = {
    "invalid_ip": "유효하지 않은 IP 주소 형식입니다",
    "ip_not_found": "해당 IP 주소를 찾을 수 없습니다",
    "invalid_month": "유효하지 않은 월 형식입니다 (YYYY-MM)",
    "month_not_found": "해당 월의 데이터가 없습니다",
    "cache_error": "캐시 작업 중 오류가 발생했습니다",
    "database_error": "데이터베이스 작업 중 오류가 발생했습니다",
    "auth_required": "인증이 필요합니다",
    "insufficient_permissions": "권한이 부족합니다",
    "rate_limit_exceeded": "요청 한도를 초과했습니다",
    "service_unavailable": "서비스를 사용할 수 없습니다",
    "internal_error": "내부 서버 오류가 발생했습니다",
    "validation_failed": "입력 데이터 검증에 실패했습니다",
    "batch_size_exceeded": f"배치 크기는 {MAX_BATCH_SIZE}개를 초과할 수 없습니다",
}

# ============ 성공 메시지 ============
SUCCESS_MESSAGES = {
    "ip_found": "IP 주소를 성공적으로 찾았습니다",
    "search_completed": "검색이 완료되었습니다",
    "cache_cleared": "캐시가 성공적으로 삭제되었습니다",
    "data_refreshed": "데이터가 성공적으로 새로고침되었습니다",
    "export_completed": "데이터 내보내기가 완료되었습니다",
    "auth_successful": "인증이 성공했습니다",
    "health_check_passed": "상태 확인이 성공했습니다",
}

# ============ 설정 검증 규칙 ============
CONFIG_VALIDATION_RULES = {
    "required_env_vars": ["BLACKLIST_USERNAME", "BLACKLIST_PASSWORD"],
    "optional_env_vars": [
        "REDIS_URL",
        "JWT_SECRET_KEY",
        "DEV_PORT",
        "PROD_PORT",
        "API_KEY_",  # API_KEY_로 시작하는 변수들
        "LOG_LEVEL",
        "DEBUG",
    ],
    "port_range": {"min": 1024, "max": 65535},
    "cache_ttl_range": {"min": 10, "max": 86400},  # 최소 10초  # 최대 24시간
}

# ============ API 엔드포인트 정의 ============
API_ENDPOINTS = {
    "health": "/health",
    "blacklist_active": "/api/blacklist/active",
    "fortigate": "/api/fortigate",
    "stats": "/api/stats",
    "search_single": "/api/search/<ip>",
    "search_batch": "/api/search/batch",
    "auth_token": "/api/auth/token",
    "admin_months": "/api/admin/months",
    "admin_month_detail": "/api/admin/month/<month>",
    "admin_cache_clear": "/api/admin/cache/clear",
}

# ============ 웹 UI 경로 ============
WEB_ROUTES = {
    "dashboard": "/",
    "data_management": "/data-management",
    "blacklist_search": "/blacklist-search",
    "connection_status": "/connection-status",
    "system_logs": "/system-logs",
}

# ============ 테스트 설정 ============
TEST_CONFIG = {
    "sample_ips": [
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "203.0.113.1",
        "198.51.100.1",
    ],
    "invalid_ips": [
        "256.256.256.256",
        "192.168.1",
        "not.an.ip.address",
        "192.168.1.1.1",
        "",
    ],
    "test_months": ["2025-06", "2025-05", "2025-04", "2024-12"],
    "invalid_months": ["2025-13", "2025-6", "25-06", "invalid-month", ""],
}

# ============ 포트 설정 ============
DEFAULT_PORT = 2541
DEV_PORT = 1541
PROD_PORT = 2541

# ============ 기본 디렉터리 설정 ============
DEFAULT_DATA_DIR = "data"
DEFAULT_LOGS_DIR = "logs"
DEFAULT_INSTANCE_DIR = "instance"

# ============ 데이터베이스 설정 ============
DEFAULT_DB_URI = "sqlite:///instance/secudium.db"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"

# ============ 업데이트 설정 ============
DEFAULT_UPDATE_INTERVAL = 3600  # 1시간
DEFAULT_BATCH_SIZE = 100
DEFAULT_TIMEOUT = 30

# ============ 개발 환경 설정 ============
DEVELOPMENT_CONFIG = {
    "debug": True,
    "auto_reload": True,
    "port": DEV_PORT,
    "host": "0.0.0.0",
    "log_level": "DEBUG",
    "cache_type": "memory",
}

# ============ 프로덕션 환경 설정 ============
PRODUCTION_CONFIG = {
    "debug": False,
    "auto_reload": False,
    "port": PROD_PORT,
    "host": "0.0.0.0",
    "log_level": "INFO",
    "cache_type": "redis",
    "workers": 4,
    "worker_timeout": 120,
}


# ============ 유틸리티 함수 ============
def get_api_endpoint(endpoint_name: str) -> str:
    """API 엔드포인트 URL 반환"""
    return API_ENDPOINTS.get(endpoint_name, "")


def get_web_route(route_name: str) -> str:
    """웹 라우트 URL 반환"""
    return WEB_ROUTES.get(route_name, "")


def get_error_message(error_key: str) -> str:
    """에러 메시지 반환"""
    return ERROR_MESSAGES.get(error_key, "알 수 없는 오류가 발생했습니다")


def get_success_message(success_key: str) -> str:
    """성공 메시지 반환"""
    return SUCCESS_MESSAGES.get(success_key, "작업이 성공적으로 완료되었습니다")


def get_cache_key(prefix: str, *args) -> str:
    """캐시 키 생성"""
    parts = [prefix] + [str(arg) for arg in args]
    return ":".join(parts)


def is_valid_ttl(ttl: int) -> bool:
    """TTL 값 유효성 검증"""
    return (
        CONFIG_VALIDATION_RULES["cache_ttl_range"]["min"]
        <= ttl
        <= CONFIG_VALIDATION_RULES["cache_ttl_range"]["max"]
    )


def is_valid_port(port: int) -> bool:
    """포트 번호 유효성 검증"""
    return (
        CONFIG_VALIDATION_RULES["port_range"]["min"]
        <= port
        <= CONFIG_VALIDATION_RULES["port_range"]["max"]
    )
