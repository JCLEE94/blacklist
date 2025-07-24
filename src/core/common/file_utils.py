"""
통합 파일 I/O 유틸리티 모듈
파일 읽기/쓰기 관련 공통 기능 제공
"""
import json
import os
from pathlib import Path
from typing import List, Set, Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class FileUtils:
    """파일 처리 관련 유틸리티 클래스"""

    @staticmethod
    def read_ip_file(
        file_path: Union[str, Path], as_set: bool = True
    ) -> Union[Set[str], List[str]]:
        """
        IP 파일 읽기 (한 줄에 하나의 IP)

        Args:
            file_path: 파일 경로
            as_set: Set으로 반환할지 여부 (중복 제거)

        Returns:
            IP 주소 목록 (Set 또는 List)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"IP file not found: {file_path}")
            return set() if as_set else []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                ips = [line.strip() for line in f if line.strip()]

            return set(ips) if as_set else ips

        except Exception as e:
            logger.error(f"Error reading IP file {file_path}: {e}")
            return set() if as_set else []

    @staticmethod
    def write_ip_file(
        file_path: Union[str, Path],
        ips: Union[Set[str], List[str]],
        sorted_output: bool = True,
    ) -> bool:
        """
        IP 파일 쓰기 (한 줄에 하나의 IP)

        Args:
            file_path: 파일 경로
            ips: IP 주소 목록
            sorted_output: 정렬하여 저장할지 여부

        Returns:
            성공 여부
        """
        file_path = Path(file_path)

        try:
            # 디렉토리 생성
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # IP 목록 준비
            ip_list = list(ips)
            if sorted_output:
                ip_list.sort()

            # 파일 쓰기
            with open(file_path, "w", encoding="utf-8") as f:
                for ip in ip_list:
                    f.write(f"{ip}\n")

            return True

        except Exception as e:
            logger.error(f"Error writing IP file {file_path}: {e}")
            return False

    @staticmethod
    def read_json_file(file_path: Union[str, Path], default: Any = None) -> Any:
        """
        JSON 파일 읽기

        Args:
            file_path: 파일 경로
            default: 파일이 없거나 에러 시 반환할 기본값

        Returns:
            JSON 데이터 또는 기본값
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return default

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}: {e}")
            return default

    @staticmethod
    def write_json_file(
        file_path: Union[str, Path], data: Any, indent: int = 2
    ) -> bool:
        """
        JSON 파일 쓰기

        Args:
            file_path: 파일 경로
            data: 저장할 데이터
            indent: 들여쓰기 크기

        Returns:
            성공 여부
        """
        file_path = Path(file_path)

        try:
            # 디렉토리 생성
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 파일 쓰기
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)

            return True

        except Exception as e:
            logger.error(f"Error writing JSON file {file_path}: {e}")
            return False

    @staticmethod
    def safe_remove(file_path: Union[str, Path]) -> bool:
        """
        안전한 파일 삭제

        Args:
            file_path: 삭제할 파일 경로

        Returns:
            성공 여부
        """
        file_path = Path(file_path)

        try:
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Error removing file {file_path}: {e}")
            return False

    @staticmethod
    def ensure_directory(dir_path: Union[str, Path]) -> Path:
        """
        디렉토리 생성 보장

        Args:
            dir_path: 생성할 디렉토리 경로

        Returns:
            생성된 디렉토리 Path 객체
        """
        dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @staticmethod
    def list_files(
        dir_path: Union[str, Path], pattern: str = "*", recursive: bool = False
    ) -> List[Path]:
        """
        디렉토리 내 파일 목록 조회

        Args:
            dir_path: 디렉토리 경로
            pattern: 파일 패턴 (glob 패턴)
            recursive: 재귀적 검색 여부

        Returns:
            파일 경로 목록
        """
        dir_path = Path(dir_path)

        if not dir_path.exists():
            return []

        if recursive:
            return list(dir_path.rglob(pattern))
        else:
            return list(dir_path.glob(pattern))
