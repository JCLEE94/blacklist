"""
URL 기반 IP 소스 플러그인
다양한 웹 소스에서 IP 리스트를 다운로드
"""

import logging
import re
from datetime import datetime
from typing import Iterator
from typing import List

import requests

from ..base_source import BaseIPSource
from ..base_source import IPEntry

logger = logging.getLogger(__name__)


class URLSource(BaseIPSource):
    """URL에서 IP 데이터를 다운로드하는 소스"""

    @property
    def source_name(self) -> str:
        return "url"

    @property
    def source_type(self) -> str:
        return "url"

    @property
    def supported_formats(self) -> List[str]:
        return ["txt", "csv", "json", "xml"]

    def validate_config(self) -> bool:
        """설정 유효성 검사"""
        url = self.config.settings.get("url")

        if not url:
            self.logger.error("Missing required setting: url")
            return False

        if not url.startswith(("http://", "https://")):
            self.logger.error("URL must start with http:// or https://")
            return False

        return True

    def fetch_data(self) -> Iterator[IPEntry]:
        """URL에서 IP 데이터 다운로드"""
        url = self.config.settings["url"]
        format_type = self.config.settings.get("format", "auto")
        category = self.config.settings.get("category", "blacklist")
        headers = self.config.settings.get("headers", {})
        timeout = self.config.settings.get("timeout", 30)

        try:
            # 기본 헤더 설정
            default_headers = {
                "User-Agent": "Nextrade-BlackList-System/2.1",
                "Accept": "*/*",
            }
            default_headers.update(headers)

            self.logger.info(f"Downloading from URL: {url}")
            response = requests.get(url, headers=default_headers, timeout=timeout)
            response.raise_for_status()

            # 형식 자동 감지
            if format_type == "auto":
                format_type = self._detect_format(response)

            # 형식별 파싱
            if format_type == "txt":
                yield from self._parse_text(response.text, category, url)
            elif format_type == "csv":
                yield from self._parse_csv(response.text, category, url)
            elif format_type == "json":
                yield from self._parse_json(response.text, category, url)
            elif format_type == "xml":
                yield from self._parse_xml(response.text, category, url)
            else:
                # 기본적으로 텍스트로 처리
                yield from self._parse_text(response.text, category, url)

        except Exception as e:
            self.logger.error(f"Failed to fetch data from URL {url}: {e}")
            raise

    def _detect_format(self, response: requests.Response) -> str:
        """응답 형식 자동 감지"""
        content_type = response.headers.get("content-type", "").lower()

        if "json" in content_type:
            return "json"
        elif "xml" in content_type:
            return "xml"
        elif "csv" in content_type:
            return "csv"
        else:
            return "txt"

    def _parse_text(self, content: str, category: str, url: str) -> Iterator[IPEntry]:
        """텍스트 형식 파싱"""
        ip_pattern = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()

            # 빈 줄이나 주석 스킵
            if not line or line.startswith(("#", "//", ";")):
                continue

            # IP 주소 찾기
            ips = ip_pattern.findall(line)
            for ip in ips:
                if self.is_valid_ip(ip):
                    yield IPEntry(
                        ip_address=ip,
                        source_name="{self.source_name}:{url}",
                        category=category,
                        confidence=1.0,
                        detection_date=datetime.utcnow(),
                        metadata={
                            "source_url": url,
                            "line_number": line_num,
                            "original_line": line,
                        },
                    )

    def _parse_csv(self, content: str, category: str, url: str) -> Iterator[IPEntry]:
        """CSV 형식 파싱"""
        import csv
        import io

        ip_column = self.config.settings.get("ip_column", 0)
        delimiter = self.config.settings.get("delimiter", ",")

        reader = csv.reader(io.StringIO(content), delimiter=delimiter)

        for line_num, row in enumerate(reader, 1):
            if len(row) <= ip_column:
                continue

            ip = row[ip_column].strip()
            if self.is_valid_ip(ip):
                # 추가 컬럼 정보를 메타데이터로 저장
                metadata = {"source_url": url, "line_number": line_num}

                for i, value in enumerate(row):
                    if i != ip_column:
                        metadata["column_{i}"] = value

                yield IPEntry(
                    ip_address=ip,
                    source_name="{self.source_name}:{url}",
                    category=category,
                    confidence=1.0,
                    detection_date=datetime.utcnow(),
                    metadata=metadata,
                )

    def _parse_json(self, content: str, category: str, url: str) -> Iterator[IPEntry]:
        """JSON 형식 파싱"""
        import json

        try:
            data = json.loads(content)

            if isinstance(data, list):
                # 단순 IP 리스트
                for ip in data:
                    if isinstance(ip, str) and self.is_valid_ip(ip):
                        yield IPEntry(
                            ip_address=ip,
                            source_name="{self.source_name}:{url}",
                            category=category,
                            confidence=1.0,
                            detection_date=datetime.utcnow(),
                            metadata={"source_url": url},
                        )
            elif isinstance(data, dict):
                # 복잡한 JSON 구조 처리
                yield from self._extract_ips_from_json(data, category, url)

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON content from {url}: {e}")

    def _parse_xml(self, content: str, category: str, url: str) -> Iterator[IPEntry]:
        """XML 형식 파싱"""
        try:
            import defusedxml.ElementTree as ET

            root = ET.fromstring(content)
            ip_pattern = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

            # XML의 모든 텍스트에서 IP 찾기
            for elem in root.iter():
                if elem.text:
                    ips = ip_pattern.findall(elem.text)
                    for ip in ips:
                        if self.is_valid_ip(ip):
                            yield IPEntry(
                                ip_address=ip,
                                source_name="{self.source_name}:{url}",
                                category=category,
                                confidence=1.0,
                                detection_date=datetime.utcnow(),
                                metadata={"source_url": url, "xml_tag": elem.tag},
                            )

        except Exception as e:
            self.logger.error(f"Error parsing XML from {url}: {e}")

    def _extract_ips_from_json(
        self, data: dict, category: str, url: str
    ) -> Iterator[IPEntry]:
        """JSON 객체에서 IP 추출"""

        def extract_ips(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = "{path}.{key}" if path else key
                    yield from extract_ips(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    yield from extract_ips(item, "{path}[{i}]")
            elif isinstance(obj, str) and self.is_valid_ip(obj):
                yield obj, path

        for ip, json_path in extract_ips(data):
            yield IPEntry(
                ip_address=ip,
                source_name="{self.source_name}:{url}",
                category=category,
                confidence=1.0,
                detection_date=datetime.utcnow(),
                metadata={"source_url": url, "json_path": json_path},
            )
