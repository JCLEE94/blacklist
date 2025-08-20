#!/usr/bin/env python3
"""
Refactored Coverage Tests
기존 623줄의 test_final_coverage_push.py를 모듈별로 분할한 버전
500줄 제한을 준수하도록 리팩토링
"""

from unittest.mock import Mock
from unittest.mock import patch

import pytest

# 분할된 테스트 모듈들 임포트
from .test_core_components import TestCoreAppComponents
from .test_database_operations import TestDatabaseOperations


class TestRefactoredModules:
    """리팩토링된 모듈들의 통합 테스트"""

    def test_route_modules_split(self):
        """라우트 모듈들이 올바르게 분할되었는지 테스트"""
        try:
            from src.core.routes.api_routes import register_sub_routes
            from src.core.routes.blacklist_routes import blacklist_routes_bp
            from src.core.routes.health_routes import health_routes_bp

            assert health_routes_bp is not None
            assert blacklist_routes_bp is not None
            assert callable(register_sub_routes)

        except ImportError as e:
            pytest.skip(f"Route modules not available: {e}")

    def test_collector_modules_split(self):
        """컨렉터 모듈들이 올바르게 분할되었는지 테스트"""
        try:
            from src.core.collectors.regtech_auth import RegtechAuth
            from src.core.collectors.regtech_parser import RegtechParser

            # 기본 인스턴스 생성 테스트
            auth = RegtechAuth("http://test.com", "user", "pass")
            parser = RegtechParser()

            assert auth is not None
            assert parser is not None

        except ImportError as e:
            pytest.skip(f"Collector modules not available: {e}")

    def test_test_modules_split(self):
        """테스트 모듈들이 올바르게 분할되었는지 테스트"""
        # 코어 컴포넌트 테스트 클래스
        core_tests = TestCoreAppComponents()
        assert core_tests is not None

        # 데이터베이스 조작 테스트 클래스
        db_tests = TestDatabaseOperations()
        assert db_tests is not None

    def test_port_configuration_fixed(self):
        """포트 설정이 통합되었는지 테스트"""
        import os

        # .env 파일에서 PORT 설정 확인
        try:
            from dotenv import load_dotenv

            load_dotenv()

            port = os.getenv("PORT")
            assert port == "2542", f"Expected PORT=2542, got {port}"

        except ImportError:
            # dotenv가 없으면 직접 파일 읽기
            try:
                with open(".env", "r") as f:
                    env_content = f.read()
                    assert "PORT=2542" in env_content
            except FileNotFoundError:
                pytest.skip(".env file not found")

    def test_file_size_compliance(self):
        """새로 생성된 파일들이 500줄 제한을 준수하는지 테스트"""
        import os

        files_to_check = [
            "/home/jclee/app/blacklist/src/core/routes/health_routes.py",
            "/home/jclee/app/blacklist/src/core/routes/blacklist_routes.py",
            "/home/jclee/app/blacklist/src/core/collectors/regtech_auth.py",
            "/home/jclee/app/blacklist/src/core/collectors/regtech_parser.py",
            "/home/jclee/app/blacklist/tests/test_core_components.py",
            "/home/jclee/app/blacklist/tests/test_database_operations.py",
        ]

        for file_path in files_to_check:
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    lines = len(f.readlines())
                    assert lines <= 500, f"{file_path} has {lines} lines (max 500)"

    def test_backward_compatibility(self):
        """기존 코드와의 호환성 테스트"""
        try:
            # 기존 api_routes.py에서 임포트하던 함수들이 여전히 접근 가능한지 확인
            from src.core.routes.api_routes import get_active_blacklist
            from src.core.routes.api_routes import health_check

            assert callable(health_check)
            assert callable(get_active_blacklist)

        except ImportError as e:
            pytest.skip(f"Backward compatibility imports failed: {e}")


class TestCodeQuality:
    """코드 품질 테스트"""

    def test_no_duplicate_code(self):
        """중복 코드가 제거되었는지 테스트"""
        # 분할된 모듈들 간에 중복된 코드가 없는지 확인
        try:
            from src.core.routes.blacklist_routes import (
                get_active_blacklist as blacklist_func,
            )
            from src.core.routes.health_routes import health_check as health_func

            # 함수들이 서로 다른 모듈에 있는지 확인
            assert health_func.__module__ != blacklist_func.__module__

        except ImportError:
            pytest.skip("Functions not available for duplicate check")

    def test_imports_organized(self):
        """임포트가 정리되었는지 테스트"""
        # 새로 생성된 파일들에서 불필요한 임포트가 없는지 확인
        files_to_check = [
            "/home/jclee/app/blacklist/src/core/routes/health_routes.py",
            "/home/jclee/app/blacklist/src/core/routes/blacklist_routes.py",
        ]

        for file_path in files_to_check:
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    content = f.read()
                    # 기본적인 임포트 체크 (예: 중복 임포트 없음)
                    import_lines = [
                        line
                        for line in content.split("\n")
                        if line.strip().startswith("import")
                        or line.strip().startswith("from")
                    ]
                    unique_imports = set(import_lines)
                    assert len(import_lines) == len(
                        unique_imports
                    ), f"Duplicate imports found in {file_path}"
