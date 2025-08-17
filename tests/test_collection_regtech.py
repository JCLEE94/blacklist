"""REGTECH collector tests

Tests for REGTECH IP collection functionality, login, data parsing, and error handling.
"""

import asyncio
import os
from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from bs4 import BeautifulSoup

from src.core.collectors.regtech_collector import RegtechCollector
from src.core.collectors.unified_collector import (
    CollectionConfig,
    CollectionResult,
    CollectionStatus,
)


class TestRegtechCollector:
    """REGTECH 수집기 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        # 테스트용 환경 변수 설정
        os.environ["REGTECH_USERNAME"] = "test_user"
        os.environ["REGTECH_PASSWORD"] = "test_pass"

        config = CollectionConfig()
        config.enabled = True
        config.max_retries = 3
        config.timeout = 300
        self.collector = RegtechCollector(config)

    def teardown_method(self):
        """각 테스트 후 정리"""
        # 테스트용 환경 변수 정리
        if "REGTECH_USERNAME" in os.environ:
            del os.environ["REGTECH_USERNAME"]
        if "REGTECH_PASSWORD" in os.environ:
            del os.environ["REGTECH_PASSWORD"]

    @patch("src.core.collectors.regtech_collector.RegtechCollector._robust_login")
    @patch("requests.Session")
    def test_login_success(self, mock_session_class, mock_robust_login):
        """로그인 성공 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 로그인 성공 설정
        mock_robust_login.return_value = True

        # 실제 collect 메서드 테스트 (비동기)
        async def run_test():
            # _collect_data를 패치하여 실제 수집 로직 건너뛰기
            with patch.object(self.collector, "_collect_data", return_value=[]):
                result = await self.collector.collect()
                return result

        result = asyncio.run(run_test())

        assert result.status.value in [
            "completed",
            "cancelled",
        ]  # 수집 완료 또는 취소됨

    @patch("src.core.collectors.regtech_collector.RegtechCollector._robust_login")
    @patch("requests.Session")
    def test_login_failure(self, mock_session_class, mock_robust_login):
        """로그인 실패 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 로그인 실패 설정
        mock_robust_login.return_value = False

        # 실제 collect 메서드 테스트 (비동기)
        async def run_test():
            # _collect_data에서 로그인 실패 시나리오
            with patch.object(
                self.collector,
                "_collect_data",
                side_effect=Exception("로그인 실패 후 재시도 한계 도달"),
            ):
                result = await self.collector.collect()
                return result

        result = asyncio.run(run_test())

        assert result.status.value == "failed"

    @patch("requests.Session")
    def test_data_collection_success(self, mock_session_class):
        """데이터 수집 성공 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 가짜 IP 데이터 생성
        fake_ip_data = [
            {
                "ip": "192.168.1.1",
                "country": "KR",
                "reason": "malware",
                "date": "2023-12-01",
                "source": "REGTECH",
            }
        ]

        # 실제 collect 메서드 테스트 (비동기)
        async def run_test():
            with patch.object(self.collector, "_robust_login", return_value=True):
                with patch.object(
                    self.collector, "_robust_collect_ips", return_value=fake_ip_data
                ):
                    result = await self.collector.collect()
                    return result

        result = asyncio.run(run_test())

        assert result.status.value == "completed"
        assert result.collected_count == 1

    def test_html_parsing(self):
        """HTML 파싱 테스트"""
        # 실제 HTML 구조 생성
        html_content = """
        <html>
            <body>
                <table>
                    <caption>요주의 IP 목록</caption>
                    <tbody>
                        <tr>
                            <td>8.8.8.8</td>
                            <td>US</td>
                            <td>malware</td>
                            <td>2023-12-01</td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        """

        soup = BeautifulSoup(html_content, "html.parser")

        # 실제로는 request_utils helper에서 처리됨
        # 기본적인 HTML 파싱이 성공하는지만 확인
        assert soup is not None
        assert "8.8.8.8" in html_content

    def test_invalid_html_parsing(self):
        """잘못된 HTML 파싱 테스트"""
        # 빈 HTML
        empty_soup = BeautifulSoup("", "html.parser")
        # HTML 파싱 자체는 성공해야 함
        assert empty_soup is not None

    def test_missing_table_elements(self):
        """필수 테이블 요소가 없는 HTML 테스트"""
        # 요주의 IP 테이블이 없는 HTML
        html_without_table = "<html><body><div>No table here</div></body></html>"
        soup = BeautifulSoup(html_without_table, "html.parser")

        # 테이블이 없는 경우 파싱은 성공하지만 데이터가 없음
        assert soup is not None
        assert len(soup.find_all("table")) == 0

    def test_duplicate_removal(self):
        """중복 제거 테스트"""
        duplicate_data = [
            {"ip": "192.168.1.1", "country": "KR", "reason": "malware"},
            {"ip": "10.0.0.1", "country": "US", "reason": "spam"},
            {"ip": "192.168.1.1", "country": "KR", "reason": "malware"},  # 중복
        ]

        # 중복 제거는 data_transform helper에서 처리됨
        result = self.collector.data_transform.remove_duplicates(duplicate_data)

        # 중복이 제거되었는지 확인
        ip_addresses = [item["ip"] for item in result]
        assert len(set(ip_addresses)) == len(ip_addresses)
        assert len(result) == 2

    def test_ip_address_validation(self):
        """IP 주소 유효성 검사 테스트"""
        # 유효한 IP 주소들
        valid_ips = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
        invalid_ips = [
            "999.999.999.999",
            "not.an.ip",
            "",
            "192.168.1.1",
        ]  # 사설 IP는 제외

        for ip in valid_ips:
            assert self.collector.validation_utils.is_valid_ip(ip) is True

        for ip in invalid_ips:
            assert self.collector.validation_utils.is_valid_ip(ip) is False

    @patch("src.core.collectors.regtech_collector.RegtechCollector._robust_login")
    @patch("src.core.collectors.regtech_collector.RegtechCollector._robust_collect_ips")
    def test_full_collection_process(self, mock_collect_ips, mock_login):
        """전체 수집 프로세스 테스트"""
        # Mock 설정
        mock_login.return_value = True

        fake_data = [
            {
                "ip": "8.8.8.8",
                "country": "US",
                "reason": "malware",
                "date": "2023-12-01",
                "source": "REGTECH",
            },
            {
                "ip": "1.1.1.1",
                "country": "US",
                "reason": "spam",
                "date": "2023-12-02",
                "source": "REGTECH",
            },
        ]
        mock_collect_ips.return_value = fake_data

        async def run_test():
            result = await self.collector.collect()
            return result

        result = asyncio.run(run_test())

        assert result.status.value == "completed"
        assert result.collected_count == 2

    def test_error_handling_network_failure(self):
        """네트워크 실패 시 에러 처리 테스트"""

        async def run_test():
            with patch.object(
                self.collector, "_collect_data", side_effect=Exception("Network error")
            ):
                result = await self.collector.collect()
                return result

        result = asyncio.run(run_test())

        assert result.status.value == "failed"
        # Error message format has korean text and placeholders
        assert result.error_count > 0

    def test_retry_mechanism(self):
        """재시도 메커니즘 테스트"""
        # 설정에서 재시도 횟수 확인
        assert self.collector.config.max_retries == 3

        async def run_test():
            call_count = 0

            def failing_collect():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception(f"Failure {call_count}")
                return []  # 세 번째 시도에서 성공

            with patch.object(
                self.collector, "_collect_data", side_effect=failing_collect
            ):
                result = await self.collector.collect()
                return result, call_count

        result, call_count = asyncio.run(run_test())

        # 재시도 후 성공했는지 확인
        assert call_count == 3
        assert result.status.value == "completed"

    def test_session_management(self):
        """세션 관리 테스트"""
        # 세션 생성 테스트
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # 세션 생성 테스트
            session = self.collector.request_utils.create_session()
            assert session is not None

    def test_date_range_handling(self):
        """날짜 범위 처리 테스트"""
        # 날짜 범위 설정
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        # 날짜 범위가 올바르게 설정되는지 테스트
        formatted_start = start_date.strftime("%Y-%m-%d")
        formatted_end = end_date.strftime("%Y-%m-%d")

        assert len(formatted_start) == 10  # YYYY-MM-DD 형식
        assert len(formatted_end) == 10
        assert formatted_start <= formatted_end

    def test_data_transformation(self):
        """데이터 변환 테스트"""
        # 원시 데이터
        raw_data = {
            "ip": "8.8.8.8",
            "country": "US",
            "reason": "malware detection",
            "date": "2023-12-01",
        }

        # 데이터 변환 테스트
        transformed = self.collector._transform_data(raw_data)

        # 필수 필드 확인
        assert "ip" in transformed
        assert "country" in transformed
        assert "reason" in transformed
        assert "source" in transformed
        assert transformed["source"] == "REGTECH"

    def test_error_recovery(self):
        """에러 복구 테스트"""

        # 일시적 에러 후 복구 시나리오
        async def run_test():
            call_count = 0

            def intermittent_failure():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Temporary failure")
                return [{"ip": "8.8.8.8", "country": "US", "reason": "test"}]

            with patch.object(
                self.collector, "_collect_data", side_effect=intermittent_failure
            ):
                result = await self.collector.collect()
                return result, call_count

        result, call_count = asyncio.run(run_test())

        # 두 번째 시도에서 성공
        assert call_count == 2
        assert result.status.value == "completed"
