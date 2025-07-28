#!/usr/bin/env python3
"""
데이터베이스 스키마 확인
"""
import sqlite3
from pathlib import Path


def check_schema():
    db_path = Path("instance/blacklist.db")
    if not db_path.exists():
        print("데이터베이스 파일이 없습니다.")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 테이블 목록
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("테이블 목록:")
    for table in tables:
        print(f"  - {table[0]}")

    # blacklist_ip 테이블 스키마
    cursor.execute("PRAGMA table_info(blacklist_ip)")
    columns = cursor.fetchall()
    print("\nblacklist_ip 테이블 스키마:")
    for col in columns:
        print(
            f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else ''} {'PRIMARY KEY' if col[5] else ''}"
        )

    # 샘플 데이터
    cursor.execute("SELECT * FROM blacklist_ip LIMIT 5")
    samples = cursor.fetchall()
    print("\n샘플 데이터:")
    for sample in samples:
        print(f"  {sample}")

    # 소스별 통계
    cursor.execute("SELECT source, COUNT(*) FROM blacklist_ip GROUP BY source")
    sources = cursor.fetchall()
    print("\n소스별 통계:")
    for source, count in sources:
        print(f"  {source}: {count}개")

    conn.close()


if __name__ == "__main__":
    check_schema()
