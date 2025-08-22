"""
데이터베이스 운영 메모리 최적화

대량 데이터베이스 연산을 메모리 효율적으로 처리하는 기능을 제공합니다.
"""

import sqlite3
from typing import Any, List

import logging
logger = logging.getLogger(__name__)


class DatabaseOptimizationMixin:
    """데이터베이스 메모리 최적화 믹스인"""

    def optimize_database_operations(
        self, db_path: str, operations: List[str]
    ) -> List[Any]:
        """데이터베이스 연산 메모리 최적화"""
        results = []

        # 단일 연결로 모든 작업 수행
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA cache_size = -64000")  # 64MB 캐시
            conn.execute("PRAGMA temp_store = MEMORY")

            cursor = conn.cursor()

            try:
                for i, operation in enumerate(operations):
                    cursor.execute(operation)

                    # 결과가 있는 경우에만 fetchall
                    if operation.strip().upper().startswith("SELECT"):
                        result = cursor.fetchall()
                        results.append(result)
                    else:
                        results.append(cursor.rowcount)

                    # 주기적 커밋 (메모리 효율성)
                    if i % 100 == 0:
                        conn.commit()

                conn.commit()

            except Exception as e:
                conn.rollback()
                logger.error(f"Database operation failed: {e}")
                raise

        return results
