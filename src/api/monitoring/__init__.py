# !/usr/bin/env python3
"""
모니터링 API 모듈
시스템 모니터링 관련 라우트들의 패키지

이 패키지는 기존의 대형 monitoring_routes.py 파일을
기능별로 분할한 결과입니다.

Modules:
- health_routes: 헬스체크 관련 라우트
- performance_routes: 성능 모니터링 라우트
- resource_routes: 시스템 리소스 모니터링 라우트
- error_routes: 에러 관리 라우트
- common_handlers: 공통 에러 핸들러
"""

from .health_routes import health_bp
from .performance_routes import performance_bp
from .resource_routes import resource_bp
from .error_routes import error_bp
from .common_handlers import register_error_handlers

__all__ = [
    "health_bp",
    "performance_bp",
    "resource_bp",
    "error_bp",
    "register_error_handlers",
]
