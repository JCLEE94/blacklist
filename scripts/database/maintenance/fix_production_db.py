#!/usr/bin/env python3
"""
운영 DB 긴급 수정 스크립트
detection_date 컬럼 추가 및 데이터 정리
"""
import os
import sqlite3
from datetime import datetime

# Docker 환경
db_path = (
    "/app/instance/blacklist.db" if os.path.exists("/app") else "instance/blacklist.db"
)

print(f"📍 DB 경로: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 현재 스키마 확인
    cursor.execute("PRAGMA table_info(blacklist_ip)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"✅ 현재 컬럼: {columns}")

    # 2. detection_date 컬럼이 없으면 추가
    if "detection_date" not in columns:
        print("🔧 detection_date 컬럼 추가 중...")
        cursor.execute(
            """
            ALTER TABLE blacklist_ip 
            ADD COLUMN detection_date TIMESTAMP
        """
        )
        print("✅ detection_date 컬럼 추가 완료")

    # 3. 기존 데이터의 detection_date를 created_at으로 설정
    cursor.execute(
        """
        UPDATE blacklist_ip 
        SET detection_date = created_at 
        WHERE detection_date IS NULL
    """
    )
    updated = cursor.rowcount
    print(f"✅ {updated}개 레코드의 detection_date 업데이트 완료")

    # 4. 월별 통계 확인
    cursor.execute(
        """
        SELECT 
            strftime('%Y-%m', detection_date) as month,
            COUNT(DISTINCT ip) as unique_ips,
            source
        FROM blacklist_ip 
        WHERE detection_date IS NOT NULL
        GROUP BY month, source
        ORDER BY month, source
    """
    )

    print("\n📊 월별 IP 통계:")
    print("월       | 소스      | IP 수")
    print("-" * 35)
    for row in cursor.fetchall():
        print(f"{row[0]} | {row[1]:8} | {row[2]:,}")

    conn.commit()
    conn.close()

    print("\n✅ 운영 DB 수정 완료!")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    if conn:
        conn.rollback()
        conn.close()
