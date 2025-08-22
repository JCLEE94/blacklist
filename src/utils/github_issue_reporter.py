"""
GitHub 이슈 자동 생성 서비스
애플리케이션 에러 발생 시 자동으로 GitHub 이슈를 생성합니다.
"""

from .common.imports import request, logger

import hashlib
import json
import os
import traceback
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional

import requests



class GitHubIssueReporter:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo_owner = os.getenv("GITHUB_REPO_OWNER", "JCLEE94")
        self.repo_name = os.getenv("GITHUB_REPO_NAME", "blacklist")
        self.base_url = (
            "https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        )
        self.session = requests.Session()

        if self.github_token:
            self.session.headers.update(
                {
                    "Authorization": "token {self.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Blacklist-Error-Reporter/1.0",
                }
            )

        # 에러 중복 방지를 위한 캐시 (메모리 기반)
        self.error_cache = {}
        self.cache_timeout = timedelta(hours=1)  # 1시간 동안 같은 에러 중복 방지
        self.max_cache_size = 1000  # 메모리 누수 방지를 위한 최대 캐시 크기
        self.max_retries = 3  # GitHub API 호출 최대 재시도 횟수
        self.retry_delay = 1  # 재시도 간격 (초)

        # 토큰 유효성 검증
        self._validate_configuration()

    def _generate_error_hash(
        self, error_type: str, error_message: str, stack_trace: str
    ) -> str:
        """에러 고유 식별자 생성"""
        content = "{error_type}:{error_message}:{stack_trace[:500]}"  # 스택트레이스 일부만 사용
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def _is_duplicate_error(self, error_hash: str) -> bool:
        """중복 에러 체크"""
        if error_hash in self.error_cache:
            last_reported = self.error_cache[error_hash]
            if datetime.now() - last_reported < self.cache_timeout:
                return True
        return False

    def _mark_error_reported(self, error_hash: str):
        """에러 보고 완료 표시"""
        self.error_cache[error_hash] = datetime.now()

    def _clean_cache(self):
        """오래된 캐시 정리 및 크기 제한 적용"""
        cutoff = datetime.now() - self.cache_timeout
        self.error_cache = {k: v for k, v in self.error_cache.items() if v > cutoff}

        # 캐시 크기가 최대 크기를 초과하는 경우 오래된 항목부터 제거
        if len(self.error_cache) > self.max_cache_size:
            # 시간순으로 정렬해서 오래된 항목부터 제거
            sorted_items = sorted(self.error_cache.items(), key=lambda x: x[1])
            items_to_keep = sorted_items[-self.max_cache_size :]
            self.error_cache = dict(items_to_keep)
            logger.info(
                "Cache size exceeded {self.max_cache_size}, cleaned to {len(self.error_cache)} items"
            )

    def _validate_configuration(self):
        """GitHub 설정 검증"""
        if not self.github_token:
            logger.warning(
                "GITHUB_TOKEN not configured. GitHub issue reporting will be disabled."
            )
        else:
            # 토큰 형식 간단 검증 (GitHub Personal Access Token은 ghp_로 시작)
            if not (
                self.github_token.startswith("ghp_")
                or self.github_token.startswith("github_pat_")
            ):
                logger.warning(
                    "GITHUB_TOKEN format may be incorrect. Expected format: ghp_* or github_pat_*"
                )

        if not self.repo_owner or not self.repo_name:
            logger.warning("GitHub repository owner or name not configured properly.")

    def test_github_connection(self) -> bool:
        """GitHub API 연결 테스트"""
        if not self.github_token:
            logger.error("Cannot test GitHub connection: GITHUB_TOKEN not configured")
            return False

        try:
            response = self.session.get("{self.base_url}", timeout=5)
            if response.status_code == 200:
                logger.info("✅ GitHub API connection test successful")
                return True
            elif response.status_code == 401:
                logger.error("❌ GitHub API authentication failed - check GITHUB_TOKEN")
                return False
            elif response.status_code == 404:
                logger.error(
                    "❌ GitHub repository not found: {self.repo_owner}/{self.repo_name}"
                )
                return False
            else:
                logger.error(f"❌ GitHub API connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ GitHub API connection test failed: {e}")
            return False

    def _format_error_title(
        self, error_type: str, error_message: str, error_hash: str
    ) -> str:
        """에러 이슈 제목 포맷"""
        # 에러 메시지를 60자로 제한
        short_message = (
            error_message[:60] + "..." if len(error_message) > 60 else error_message
        )
        return f"🚨 {error_type}: {short_message} ({error_hash})"

    def _format_error_body(self, error_data: Dict[str, Any]) -> str:
        """에러 이슈 본문 포맷"""
        timestamp = error_data.get("timestamp", datetime.now().isoformat())
        error_type = error_data.get("error_type", "Unknown")
        error_message = error_data.get("error_message", "No message")
        stack_trace = error_data.get("stack_trace", "No stack trace")
        context = error_data.get("context", {})
        user_agent = error_data.get("user_agent", "Unknown")
        request_path = error_data.get("request_path", "Unknown")
        request_method = error_data.get("request_method", "Unknown")
        server_info = error_data.get("server_info", {})

        body = f"""## 🚨 자동 에러 리포트

### 📊 에러 정보
- **발생 시간**: {timestamp}
- **에러 타입**: `{error_type}`
- **에러 메시지**: {error_message}

### 🔍 요청 정보
- **요청 경로**: `{request_path}`
- **HTTP 메서드**: `{request_method}`
- **User Agent**: {user_agent}

### 🖥️ 서버 환경
- **호스트**: {server_info.get('hostname', 'Unknown')}
- **Python 버전**: {server_info.get('python_version', 'Unknown')}
- **Flask 버전**: {server_info.get('flask_version', 'Unknown')}

### 📝 스택 트레이스
```python
{stack_trace}
```

### 🧩 컨텍스트 정보
```json
{json.dumps(context, indent=2, ensure_ascii=False)}
```

### 🏷️ 라벨
- `bug` - 버그 관련
- `auto-generated` - 자동 생성됨
- `error-report` - 에러 리포트
- `priority-high` - 높은 우선순위

---
*이 이슈는 Blacklist 애플리케이션에서 자동으로 생성되었습니다.*
*발생 시간: {timestamp}*
"""
        return body

    def create_issue(self, error_data: Dict[str, Any]) -> Optional[str]:
        """GitHub 이슈 생성"""
        try:
            if not self.github_token:
                logger.warning("GitHub token not configured. Skipping issue creation.")
                return None

            # 에러 고유 식별자 생성
            error_hash = self._generate_error_hash(
                error_data.get("error_type", ""),
                error_data.get("error_message", ""),
                error_data.get("stack_trace", ""),
            )

            # 중복 에러 체크
            if self._is_duplicate_error(error_hash):
                logger.info(f"Duplicate error {error_hash}, skipping issue creation")
                return None

            # 캐시 정리
            self._clean_cache()

            # 이슈 데이터 구성
            title = self._format_error_title(
                error_data.get("error_type", "Unknown"),
                error_data.get("error_message", ""),
                error_hash,
            )
            body = self._format_error_body(error_data)

            issue_data = {
                "title": title,
                "body": body,
                "labels": ["bug", "auto-generated", "error-report", "priority-high"],
            }

            # GitHub API 호출 (재시도 로직 포함)
            for attempt in range(self.max_retries):
                try:
                    response = self.session.post(
                        "{self.base_url}/issues", json=issue_data, timeout=10
                    )

                    if response.status_code == 201:
                        issue_url = response.json().get("html_url")
                        logger.info(f"GitHub issue created successfully: {issue_url}")

                        # 에러 보고 완료 표시
                        self._mark_error_reported(error_hash)

                        return issue_url
                    elif response.status_code == 401:
                        logger.error(
                            "GitHub API authentication failed - check GITHUB_TOKEN"
                        )
                        return None
                    elif response.status_code == 403:
                        logger.error(
                            "GitHub API rate limit exceeded or permission denied"
                        )
                        return None
                    elif response.status_code >= 500:
                        # 서버 에러의 경우 재시도
                        logger.warning(
                            f"GitHub API server error (attempt {attempt + 1}/{self.max_retries}): {response.status_code}"
                        )
                        if attempt < self.max_retries - 1:
                            import time

                            time.sleep(self.retry_delay * (attempt + 1))  # 지수 백오프
                            continue
                    else:
                        logger.error(
                            "Failed to create GitHub issue: {response.status_code} - {response.text}"
                        )
                        return None

                except requests.exceptions.Timeout:
                    logger.warning(
                        "GitHub API timeout (attempt {attempt + 1}/{self.max_retries})"
                    )
                    if attempt < self.max_retries - 1:
                        import time

                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                except requests.exceptions.RequestException as e:
                    logger.warning(
                        f"GitHub API request error (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    if attempt < self.max_retries - 1:
                        import time

                        time.sleep(self.retry_delay * (attempt + 1))
                        continue

                # 마지막 시도에서도 실패한 경우
                if attempt == self.max_retries - 1:
                    logger.error("GitHub API call failed after all retry attempts")
                    return None

        except Exception as e:
            logger.error(f"Error creating GitHub issue: {e}")
            return None

    def report_exception(
        self, exc: Exception, context: Dict[str, Any] = None
    ) -> Optional[str]:
        """예외를 GitHub 이슈로 리포트"""
        try:
            import platform
            import sys

            import flask

            error_data = {
                "timestamp": datetime.now().isoformat(),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "stack_trace": traceback.format_exc(),
                "context": context or {},
                "server_info": {
                    "hostname": platform.node(),
                    "python_version": sys.version,
                    "flask_version": getattr(flask, "__version__", "Unknown"),
                    "platform": platform.platform(),
                },
            }

            # Flask 컨텍스트에서 요청 정보 추출
            try:
                
                if has_request_context():
                    error_data.update(
                        {
                            "request_path": request.path,
                            "request_method": request.method,
                            "user_agent": request.headers.get("User-Agent", "Unknown"),
                            "remote_addr": request.remote_addr,
                        }
                    )
            except Exception:
                pass

            return self.create_issue(error_data)

        except Exception as e:
            logger.error(f"Error in report_exception: {e}")
            return None


# 전역 리포터 인스턴스
_reporter = None


def get_github_reporter() -> GitHubIssueReporter:
    """GitHub 리포터 싱글톤 인스턴스 반환"""
    global _reporter
    if _reporter is None:
        _reporter = GitHubIssueReporter()
    return _reporter


def report_error_to_github(
    exc: Exception, context: Dict[str, Any] = None
) -> Optional[str]:
    """에러를 GitHub 이슈로 리포트하는 편의 함수"""
    reporter = get_github_reporter()
    return reporter.report_exception(exc, context)


def github_error_handler(func):
    """데코레이터: 함수 실행 중 에러 발생 시 자동으로 GitHub 이슈 생성"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # GitHub 이슈 생성
            context = {
                "function_name": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
            }
            report_error_to_github(e, context)
            # 원래 예외를 다시 발생시킴
            raise

    return wrapper
