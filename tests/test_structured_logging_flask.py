#!/usr/bin/env python3
"""
Flask integration tests for src/utils/structured_logging.py
Flask request logging setup and API endpoint tests
"""

import json
import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask

from src.utils.structured_logging import get_logger, setup_request_logging


class TestFlaskIntegration(unittest.TestCase):
    """Flask 통합 테스트"""

    def test_setup_request_logging_basic(self):
        """Flask 요청 로깅 설정 기본 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        # before_request 및 after_request 핸들러가 등록되었는지 확인
        self.assertGreater(len(app.before_request_funcs[None]), 0)
        self.assertGreater(len(app.after_request_funcs[None]), 0)

    def test_setup_request_logging_with_context(self):
        """Flask 요청 로깅 컨텍스트 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        with app.test_request_context("/test"):
            with app.app_context():
                # before_request 실행
                for func in app.before_request_funcs[None]:
                    func()

                # request_id와 start_time이 설정되었는지 확인
                from flask import g

                self.assertTrue(hasattr(g, "request_id"))
                self.assertTrue(hasattr(g, "start_time"))
                self.assertTrue(hasattr(g, "log_start_time"))

    def test_setup_request_logging_after_request(self):
        """Flask 요청 로깅 after_request 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        with app.test_request_context():
            with app.app_context():
                # before_request 실행
                for func in app.before_request_funcs[None]:
                    func()

                # Mock response
                mock_response = MagicMock()
                mock_response.status_code = 200

                # after_request 실행
                for func in app.after_request_funcs[None]:
                    result = func(mock_response)
                    self.assertEqual(result, mock_response)

    def test_log_stats_endpoint(self):
        """로그 통계 API 엔드포인트 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        with app.test_client() as client:
            response = client.get("/api/logs/stats")
            self.assertEqual(response.status_code, 200)

            # JSON 응답인지 확인
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)

    def test_log_search_endpoint_success(self):
        """로그 검색 API 엔드포인트 성공 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        with app.test_client() as client:
            response = client.get("/api/logs/search?q=test&limit=50")
            self.assertEqual(response.status_code, 200)

            # JSON 응답인지 확인
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)

    def test_log_search_endpoint_missing_query(self):
        """로그 검색 API 엔드포인트 쿼리 누락 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        with app.test_client() as client:
            response = client.get("/api/logs/search")
            self.assertEqual(response.status_code, 400)

            data = json.loads(response.data)
            self.assertIn("error", data)

    def test_log_search_endpoint_limit_validation(self):
        """로그 검색 API 엔드포인트 제한 검증 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        with app.test_client() as client:
            # 제한값이 1000을 초과하는 경우
            response = client.get("/api/logs/search?q=test&limit=2000")
            self.assertEqual(response.status_code, 200)

    def test_flask_integration_full_workflow(self):
        """Flask 통합 풀 워크플로우 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        @app.route("/test")
        def test_endpoint():
            logger = get_logger("flask_test")
            logger.info("Request processed")
            return {"status": "success"}

        with app.test_client() as client:
            response = client.get("/test")
            self.assertEqual(response.status_code, 200)

            # 로그가 기록되었는지 확인
            logger = get_logger("request")
            stats = logger.get_log_stats()
            self.assertGreater(stats["stats"]["info"], 0)

    def test_request_id_generation(self):
        """요청 ID 생성 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        request_ids = set()

        @app.route("/test-id")
        def test_id_endpoint():
            from flask import g

            request_ids.add(g.request_id)
            return {"request_id": g.request_id}

        with app.test_client() as client:
            # 여러 요청 전송
            for _ in range(5):
                response = client.get("/test-id")
                self.assertEqual(response.status_code, 200)

        # 다른 request_id가 생성되었는지 확인
        self.assertEqual(len(request_ids), 5)

    def test_performance_logging(self):
        """성능 로깅 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        @app.route("/slow-endpoint")
        def slow_endpoint():
            import time

            time.sleep(0.1)  # 지연 시뮬레이션
            return {"status": "completed"}

        with app.test_client() as client:
            response = client.get("/slow-endpoint")
            self.assertEqual(response.status_code, 200)

            # 성능 로그가 기록되었는지 확인
            logger = get_logger("request")
            recent_logs = logger.get_recent_logs(count=5)

            # 응답 시간이 기록되었는지 확인
            performance_logs = [
                log for log in recent_logs if "response_time" in log.get("context", {})
            ]
            self.assertGreater(len(performance_logs), 0)

    def test_error_logging_integration(self):
        """에러 로깅 통합 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        @app.route("/error-endpoint")
        def error_endpoint():
            logger = get_logger("flask_error_test")
            try:
                raise ValueError("Test error for logging")
            except ValueError as e:
                logger.error("Error in endpoint", exception=e)
                return {"error": "Internal error"}, 500

        with app.test_client() as client:
            response = client.get("/error-endpoint")
            self.assertEqual(response.status_code, 500)

            # 에러 로그가 기록되었는지 확인
            logger = get_logger("flask_error_test")
            stats = logger.get_log_stats()
            self.assertGreater(stats["stats"]["error"], 0)

            # 예외 정보가 포함되었는지 확인
            recent_errors = stats["recent_errors"]
            self.assertGreater(len(recent_errors), 0)

            error_log = recent_errors[0]
            self.assertIn("exception", error_log)
            self.assertEqual(error_log["exception"]["type"], "ValueError")

    def test_context_preservation(self):
        """컨텍스트 보존 테스트"""
        app = Flask(__name__)
        app.testing = True

        setup_request_logging(app)

        @app.route("/context-test")
        def context_test():
            from flask import g

            logger = get_logger("context_test")

            # 커스텀 컨텍스트 추가
            g.user_id = "test_user_123"
            g.session_id = "session_456"

            logger.info("Context test message")

            return {
                "request_id": g.request_id,
                "user_id": g.user_id,
                "session_id": g.session_id,
            }

        with app.test_client() as client:
            response = client.get("/context-test")
            self.assertEqual(response.status_code, 200)

            # 컨텍스트가 로그에 포함되었는지 확인
            logger = get_logger("context_test")
            recent_logs = logger.get_recent_logs(count=1)

            self.assertEqual(len(recent_logs), 1)
            log_context = recent_logs[0].get("context", {})

            # Flask 요청 컨텍스트가 포함되었는지 확인
            self.assertIn("request", log_context)
            self.assertIn("request_id", log_context)
            self.assertEqual(log_context["request"]["path"], "/context-test")


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
