#!/usr/bin/env python3
"""
운영 데이터베이스 스키마 수정 스크립트
detection_date 컬럼 추가
"""

import os
import sqlite3
import sys
from datetime import datetime


def fix_database_schema():
    """데이터베이스 스키마 수정"""

    # 데이터베이스 경로들
    db_paths = [
        '/app/instance/blacklist.db',
        'instance/blacklist.db',
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'instance', 'blacklist.db'
        ),
    ]

    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print("ERROR: 데이터베이스 파일을 찾을 수 없습니다")
        sys.exit(1)

    print(f"데이터베이스 경로: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 현재 스키마 확인
        cursor.execute("PRAGMA table_info(blacklist_ip)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        print(f"현재 컬럼: {column_names}")

        # detection_date 컬럼이 없으면 추가
        if 'detection_date' not in column_names:
            print("detection_date 컬럼 추가 중...")
            cursor.execute(
                """
                ALTER TABLE blacklist_ip 
                ADD COLUMN detection_date TIMESTAMP
            """
            )
            print("✅ detection_date 컬럼 추가 완료")
        else:
            print("detection_date 컬럼이 이미 존재합니다")

        # 다른 누락된 컬럼들도 확인 및 추가
        missing_columns = {
            'reason': 'TEXT',
            'threat_level': 'VARCHAR(20)',
            'is_active': 'BOOLEAN DEFAULT 1',
            'updated_at': 'TIMESTAMP',
        }

        for col_name, col_type in missing_columns.items():
            if col_name not in column_names:
                print(f"{col_name} 컬럼 추가 중...")
                cursor.execute(
                    f"""
                    ALTER TABLE blacklist_ip 
                    ADD COLUMN {col_name} {col_type}
                """
                )
                print(f"✅ {col_name} 컬럼 추가 완료")

        conn.commit()

        # 최종 스키마 확인
        cursor.execute("PRAGMA table_info(blacklist_ip)")
        columns = cursor.fetchall()
        print("\n최종 테이블 스키마:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        # 데이터 개수 확인
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
        count = cursor.fetchone()[0]
        print(f"\n현재 저장된 IP 개수: {count}")

        # collection_logs 테이블도 확인
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='collection_logs'
        """
        )
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM collection_logs")
            log_count = cursor.fetchone()[0]
            print(f"수집 로그 개수: {log_count}")
        else:
            print("collection_logs 테이블이 없습니다")

    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

    print("\n✅ 데이터베이스 스키마 수정 완료!")


if __name__ == "__main__":
    fix_database_schema()
