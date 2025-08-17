"""
외부 서비스 및 시스템 모킹 픽스처
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest


class MockResponse:
    """HTTP 응답 모킹 클래스"""

    def __init__(self, json_data=None, status_code=200, content=b"", headers=None):
        self.json_data = json_data or {}
        self.status_code = status_code
        self.content = content
        self.text = content.decode() if isinstance(content, bytes) else str(content)
        self.headers = headers or {}

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} Error")


@pytest.fixture
def mock_external_services():
    """외부 API 서비스 모킹"""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:

        # REGTECH API 응답
        mock_get.return_value = MockResponse(
            json_data={"status": "success", "data": []}, status_code=200
        )

        # SECUDIUM API 응답
        mock_post.return_value = MockResponse(
            json_data={"result": "ok", "token": "test-token"}, status_code=200
        )

        yield {"get": mock_get, "post": mock_post}


@pytest.fixture
def mock_subprocess():
    """subprocess 모킹"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_file_system():
    """파일 시스템 모킹"""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_file", return_value=True),
        patch("pathlib.Path.is_dir", return_value=True),
        patch("builtins.open", create=True) as mock_open,
    ):

        # 파일 내용 모킹
        mock_open.return_value.__enter__.return_value.read.return_value = "test content"
        mock_open.return_value.__enter__.return_value.readlines.return_value = [
            "line1\n",
            "line2\n",
        ]

        yield {"open": mock_open}


@contextmanager
def does_not_raise():
    """예외가 발생하지 않음을 나타내는 컨텍스트 매니저"""
    yield
