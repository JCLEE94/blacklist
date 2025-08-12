"""
파일 기반 IP 소스 플러그인
다양한 형식의 IP 리스트 파일을 지원
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterator, List

from ..base_source import BaseIPSource, IPEntry

logger = logging.getLogger(__name__)


class FileSource(BaseIPSource):
    """파일에서 IP 데이터를 읽어오는 소스"""

    @property
    def source_name(self) -> str:
        return "file"

    @property
    def source_type(self) -> str:
        return "file"

    @property
    def supported_formats(self) -> List[str]:
        return ["txt", "csv", "json", "log"]

    def validate_config(self) -> bool:
        """설정 유효성 검사"""
        file_path = self.config.settings.get("file_path")

        if not file_path:
            self.logger.error("Missing required setting: file_path")
            return False

        if not os.path.exists(file_path):
            self.logger.error("File not found: {file_path}")
            return False

        return True

    def fetch_data(self) -> Iterator[IPEntry]:
        """파일에서 IP 데이터 읽기"""
        file_path = self.config.settings["file_path"]
        file_format = self.config.settings.get("format", "auto")
        delimiter = self.config.settings.get("delimiter", None)
        ip_column = self.config.settings.get("ip_column", 0)
        category = self.config.settings.get("category", "blacklist")

        try:
            # 파일 형식 자동 감지
            if file_format == "auto":
                file_format = self._detect_format(file_path)

            # 형식별 파싱
            if file_format == "txt":
                yield from self._parse_text_file(file_path, category)
            elif file_format == "csv":
                yield from self._parse_csv_file(
                    file_path, delimiter, ip_column, category
                )
            elif file_format == "json":
                yield from self._parse_json_file(file_path, category)
            elif file_format == "log":
                yield from self._parse_log_file(file_path, category)
            else:
                raise ValueError("Unsupported file format: {file_format}")

        except Exception as e:
            self.logger.error("Failed to parse file {file_path}: {e}")
            raise

    def _detect_format(self, file_path: str) -> str:
        """파일 형식 자동 감지"""
        extension = Path(file_path).suffix.lower()

        format_map = {
            ".txt": "txt",
            ".csv": "csv",
            ".json": "json",
            ".log": "log",
            ".tsv": "csv",
        }

        return format_map.get(extension, "txt")

    def _parse_text_file(self, file_path: str, category: str) -> Iterator[IPEntry]:
        """텍스트 파일 파싱 (한 줄에 하나의 IP)"""
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # 빈 줄이나 주석 스킵
                if not line or line.startswith("#"):
                    continue

                # IP 주소 추출
                ip = self._extract_ip_from_line(line)
                if ip and self.is_valid_ip(ip):
                    yield IPEntry(
                        ip_address=ip,
                        source_name="{self.source_name}:{Path(file_path).name}",
                        category=category,
                        confidence=1.0,
                        detection_date=datetime.utcnow(),
                        metadata={
                            "file_path": file_path,
                            "line_number": line_num,
                            "original_line": line,
                        },
                    )

    def _parse_csv_file(
        self, file_path: str, delimiter: str, ip_column: int, category: str
    ) -> Iterator[IPEntry]:
        """CSV 파일 파싱"""
        import csv

        if delimiter is None:
            # 자동 구분자 감지
            with open(file_path, "r", encoding="utf-8") as f:
                sample = f.read(1024)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=delimiter)

            for line_num, row in enumerate(reader, 1):
                if len(row) <= ip_column:
                    continue

                ip = row[ip_column].strip()
                if self.is_valid_ip(ip):
                    # 추가 컬럼 정보를 메타데이터로 저장
                    metadata = {"file_path": file_path, "line_number": line_num}

                    # 다른 컬럼들을 메타데이터에 추가
                    for i, value in enumerate(row):
                        if i != ip_column:
                            metadata["column_{i}"] = value

                    yield IPEntry(
                        ip_address=ip,
                        source_name="{self.source_name}:{Path(file_path).name}",
                        category=category,
                        confidence=1.0,
                        detection_date=datetime.utcnow(),
                        metadata=metadata,
                    )

    def _parse_json_file(self, file_path: str, category: str) -> Iterator[IPEntry]:
        """JSON 파일 파싱"""
        import json

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # JSON 구조 자동 감지
        if isinstance(data, list):
            # 단순 IP 리스트
            for ip in data:
                if isinstance(ip, str) and self.is_valid_ip(ip):
                    yield IPEntry(
                        ip_address=ip,
                        source_name="{self.source_name}:{Path(file_path).name}",
                        category=category,
                        confidence=1.0,
                        detection_date=datetime.utcnow(),
                        metadata={"file_path": file_path},
                    )
        elif isinstance(data, dict):
            # 복잡한 JSON 구조 처리
            yield from self._parse_json_object(data, file_path, category)

    def _parse_json_object(
        self, data: dict, file_path: str, category: str
    ) -> Iterator[IPEntry]:
        """복잡한 JSON 객체 파싱"""

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
                source_name="{self.source_name}:{Path(file_path).name}",
                category=category,
                confidence=1.0,
                detection_date=datetime.utcnow(),
                metadata={"file_path": file_path, "json_path": json_path},
            )

    def _parse_log_file(self, file_path: str, category: str) -> Iterator[IPEntry]:
        """로그 파일에서 IP 추출"""
        # 일반적인 IP 패턴
        ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # 모든 IP 주소 찾기
                ips = ip_pattern.findall(line)

                for ip in ips:
                    if self.is_valid_ip(ip):
                        yield IPEntry(
                            ip_address=ip,
                            source_name="{self.source_name}:{Path(file_path).name}",
                            category=category,
                            confidence=0.8,  # 로그에서 추출한 IP는 확신도 낮음
                            detection_date=datetime.utcnow(),
                            metadata={
                                "file_path": file_path,
                                "line_number": line_num,
                                "log_line": line.strip(),
                            },
                        )

    def _extract_ip_from_line(self, line: str) -> str:
        """라인에서 IP 주소 추출"""
        # 여러 형식 지원
        # 1. 순수 IP: "192.168.1.1"
        # 2. CIDR: "192.168.1.1/24" -> "192.168.1.1"
        # 3. 포트 포함: "192.168.1.1:80" -> "192.168.1.1"
        # 4. 공백으로 구분된 필드

        # 공백으로 분할하여 첫 번째 필드 사용
        parts = line.split()
        if not parts:
            return None

        ip_candidate = parts[0]

        # CIDR 표기 처리
        if "/" in ip_candidate:
            ip_candidate = ip_candidate.split("/")[0]

        # 포트 번호 제거
        if ":" in ip_candidate:
            ip_candidate = ip_candidate.split(":")[0]

        return ip_candidate
