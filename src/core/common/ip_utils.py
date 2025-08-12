"""
통합 IP 유틸리티 모듈
모든 IP 관련 검증 및 처리 로직을 통합
"""

import ipaddress
import re
from typing import List
from typing import Optional
from typing import Tuple


class IPUtils:
    """IP 주소 관련 유틸리티 클래스"""

    # 정규식 패턴 (성능을 위해 컴파일된 패턴 캐싱)
    _IP_PATTERN = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
    _IP_EXTRACT_PATTERN = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

    # 내부 IP 대역
    _PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ]

    @classmethod
    def validate_ip(cls, ip_address: str) -> bool:
        """
        IP 주소 형식 검증 (통합 메서드)

        Args:
            ip_address: 검증할 IP 주소

        Returns:
            유효한 IP 주소인 경우 True
        """
        if not ip_address or not isinstance(ip_address, str):
            return False

        # 빠른 정규식 검사
        if not cls._IP_PATTERN.match(ip_address):
            return False

        # 정확한 검증
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False

    @classmethod
    def sanitize_ip(cls, ip_address: str) -> Optional[str]:
        """
        IP 주소 정리 및 정규화

        Args:
            ip_address: 정리할 IP 주소

        Returns:
            정규화된 IP 주소 또는 None
        """
        if not ip_address:
            return None

        ip = ip_address.strip()

        # 검증
        if not cls.validate_ip(ip):
            return None

        # 앞의 0 제거 (예: 001.002.003.004 -> 1.2.3.4)
        try:
            return str(ipaddress.ip_address(ip))
        except ValueError:
            return None

    @classmethod
    def extract_ips_from_text(
        cls, text: str, exclude_private: bool = True
    ) -> List[str]:
        """
        텍스트에서 IP 주소 추출

        Args:
            text: IP를 추출할 텍스트
            exclude_private: 내부 IP 제외 여부

        Returns:
            추출된 IP 주소 목록
        """
        found_ips = cls._IP_EXTRACT_PATTERN.findall(text)
        valid_ips = []

        for ip in found_ips:
            if cls.validate_ip(ip):
                if exclude_private and cls.is_private_ip(ip):
                    continue
                valid_ips.append(ip)

        return list(set(valid_ips))  # 중복 제거

    @classmethod
    def is_private_ip(cls, ip_address: str) -> bool:
        """
        내부(사설) IP 주소인지 확인

        Args:
            ip_address: 확인할 IP 주소

        Returns:
            내부 IP인 경우 True
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            return any(ip in network for network in cls._PRIVATE_RANGES)
        except ValueError:
            return False

    @classmethod
    def validate_ip_list(
        cls, ip_list: List[str], max_count: int = 100
    ) -> Tuple[List[str], List[str]]:
        """
        IP 리스트 검증 (기존 validators.py 호환)

        Args:
            ip_list: 검증할 IP 목록
            max_count: 최대 허용 개수

        Returns:
            (valid_ips, invalid_ips)
        """
        if len(ip_list) > max_count:
            ip_list = ip_list[:max_count]

        valid_ips = []
        invalid_ips = []

        for ip in ip_list:
            if cls.validate_ip(ip):
                valid_ips.append(ip)
            else:
                invalid_ips.append(ip)

        return valid_ips, invalid_ips

    @classmethod
    def get_subnet(cls, ip_address: str, prefix_length: int = 24) -> Optional[str]:
        """
        IP 주소의 서브넷 반환

        Args:
            ip_address: IP 주소
            prefix_length: 서브넷 프리픽스 길이

        Returns:
            서브넷 문자열 (예: "192.168.1.0/24")
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            network = ipaddress.ip_network(f"{ip}/{prefix_length}", strict=False)
            return str(network)
        except ValueError:
            return None

    @classmethod
    def is_in_cidr(cls, ip_address: str, cidr: str) -> bool:
        """
        IP가 특정 CIDR 범위에 속하는지 확인

        Args:
            ip_address: 확인할 IP 주소
            cidr: CIDR 표기법 네트워크

        Returns:
            CIDR 범위에 속하면 True
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            network = ipaddress.ip_network(cidr, strict=False)
            return ip in network
        except ValueError:
            return False


# 기존 함수들과의 호환성을 위한 래퍼 함수들
def validate_ip(ip_address: str) -> bool:
    """IP 주소 형식 검증 (후방 호환성)"""
    return IPUtils.validate_ip(ip_address)


def sanitize_ip(ip_address: str) -> Optional[str]:
    """IP 주소 정리 및 정규화 (후방 호환성)"""
    return IPUtils.sanitize_ip(ip_address)


def validate_ip_list(
    ip_list: List[str], max_count: int = 100
) -> Tuple[List[str], List[str]]:
    """IP 리스트 검증 (후방 호환성)"""
    return IPUtils.validate_ip_list(ip_list, max_count)
