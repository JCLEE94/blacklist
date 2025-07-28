#!/usr/bin/env python3
"""
데이터베이스의 detection_date 컬럼 확인 스크립트
"""

import sqlite3
import sys
from collections import Counter
from datetime import datetime


def check_detection_dates():
    """detection_date 컬럼의 데이터 분포 확인"""

    # 로컬 개발 데이터베이스 확인
    local_db = "/home/jclee/app/blacklist/instance/blacklist.db"

    try:
        print("🔍 로컬 데이터베이스 확인 중...")
        with sqlite3.connect(local_db) as conn:
            cursor = conn.cursor()

            # 테이블 구조 확인
            cursor.execute("PRAGMA table_info(blacklist_ip)")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 테이블 컬럼: {columns}")

            if 'detection_date' not in columns:
                print("❌ detection_date 컬럼이 없습니다")
                return

            # 전체 IP 수
            cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
            total_count = cursor.fetchone()[0]
            print(f"📊 전체 IP 수: {total_count:,}")

            # detection_date 분포 확인
            cursor.execute(
                """
                SELECT 
                    DATE(detection_date) as date,
                    COUNT(*) as count
                FROM blacklist_ip 
                WHERE detection_date IS NOT NULL
                GROUP BY DATE(detection_date)
                ORDER BY date DESC
                LIMIT 10
            """
            )

            date_distribution = cursor.fetchall()
            print("\n📅 탐지일 분포 (최근 10일):")
            for date, count in date_distribution:
                print(f"  {date}: {count:,}개")

            # 샘플 데이터 확인
            cursor.execute(
                """
                SELECT ip_address, detection_date, reg_date, source
                FROM blacklist_ip 
                ORDER BY RANDOM()
                LIMIT 5
            """
            )

            samples = cursor.fetchall()
            print("\n🔍 샘플 데이터:")
            for ip, det_date, reg_date, source in samples:
                print(
                    f"  IP: {ip}, 탐지일: {det_date}, 등록일: {reg_date}, 소스: {source}"
                )

            # NULL 검사
            cursor.execute(
                "SELECT COUNT(*) FROM blacklist_ip WHERE detection_date IS NULL"
            )
            null_count = cursor.fetchone()[0]
            print(f"\n⚠️  detection_date가 NULL인 IP: {null_count:,}개")

            # 오늘 날짜와 다른 탐지일 확인
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute(
                """
                SELECT COUNT(*) FROM blacklist_ip 
                WHERE DATE(detection_date) != ?
            """,
                (today,),
            )
            different_date_count = cursor.fetchone()[0]
            print(f"📈 오늘과 다른 탐지일을 가진 IP: {different_date_count:,}개")

    except Exception as e:
        print(f"❌ 로컬 DB 확인 실패: {e}")


if __name__ == "__main__":
    check_detection_dates()
