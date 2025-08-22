#!/usr/bin/env python3
"""
인증 관리 모듈
인증 설정, REGTECH, SECUDIUM 관련 라우트들의 패키지

이 패키지는 기존의 대형 auth_routes.py 파일을
기능별로 분할한 결과입니다.

Modules:
- config_routes: 인증 설정 조회/저장 라우트
- regtech_routes: REGTECH 인증 관리 라우트
- secudium_routes: SECUDIUM 인증 관리 라우트
"""

from .config_routes import config_bp
from .regtech_routes import regtech_bp
from .secudium_routes import secudium_bp

__all__ = ["config_bp", "regtech_bp", "secudium_bp"]
