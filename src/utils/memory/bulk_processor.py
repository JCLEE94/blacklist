"""
대량 데이터 처리 메모리 최적화

대량의 IP 데이터를 메모리 효율적으로 처리하는 기능을 제공합니다.
"""

from typing import List

from loguru import logger

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class BulkProcessorMixin:
    """대량 데이터 처리 메모리 최적화 믹스인"""

    def efficient_ip_processing(self, ip_list: List[str]) -> List[str]:
        """대량 IP 처리 메모리 최적화"""
        if not ip_list:
            return []

        # numpy 사용 가능하면 벡터화 처리
        if HAS_NUMPY and len(ip_list) > 10000:
            logger.info(f"Using numpy for efficient processing of {len(ip_list)} IPs")

            # numpy 배열로 변환 (메모리 효율적)
            ip_array = np.array(ip_list, dtype="U15")  # 최대 15자 IP 주소

            # 중복 제거 (numpy는 메모리 효율적)
            unique_ips = np.unique(ip_array)

            return unique_ips.tolist()

        else:
            # 표준 Python 최적화
            logger.info(f"Using standard Python for processing {len(ip_list)} IPs")

            # 집합을 사용한 중복 제거 (메모리 효율적)
            unique_ips = set()

            # 청크 단위로 처리 - simple chunking implementation
            chunk_size = 5000
            total_chunks = (len(ip_list) + chunk_size - 1) // chunk_size

            for i in range(0, len(ip_list), chunk_size):
                chunk = ip_list[i : i + chunk_size]
                chunk_num = i // chunk_size + 1
                unique_ips.update(chunk)

                if chunk_num % 5 == 0:
                    logger.debug(f"Processed chunk {chunk_num}/{total_chunks}")

            return list(unique_ips)
