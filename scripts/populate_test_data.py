#!/usr/bin/env python3
"""
테스트 데이터 생성 및 데이터베이스 저장
"""

import sqlite3
from datetime import datetime, timedelta
import random
import json


def create_test_data():
    """테스트 블랙리스트 데이터 생성"""

    # SQLite 데이터베이스 연결
    conn = sqlite3.connect("instance/blacklist.db")
    cursor = conn.cursor()

    # 테이블 생성 (없으면)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            source TEXT,
            threat_level TEXT,
            description TEXT,
            country TEXT,
            detection_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            UNIQUE(ip_address, source)
        )
    """
    )

    # 기존 데이터 삭제
    cursor.execute("DELETE FROM blacklist WHERE source LIKE '%TEST%'")

    print("📊 테스트 데이터 생성 중...")

    # 최근 30일간의 데이터 생성
    base_date = datetime.now() - timedelta(days=30)
    total_inserted = 0

    for day in range(30):
        date = base_date + timedelta(days=day)
        date_str = date.strftime("%Y-%m-%d")

        # 하루에 50-150개의 IP 생성
        num_ips = random.randint(50, 150)

        for i in range(num_ips):
            ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
            source = random.choice(["REGTECH_TEST", "SECUDIUM_TEST"])
            threat_level = random.choice(["high", "medium", "low"])
            country = random.choice(["CN", "RU", "US", "KR", "JP", "VN", "TH"])
            description = f"Test threat from {country} - Level: {threat_level}"

            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO blacklist 
                    (ip_address, source, threat_level, description, country, detection_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (ip, source, threat_level, description, country, date_str, 1),
                )

                if cursor.rowcount > 0:
                    total_inserted += 1

            except Exception as e:
                print(f"  ⚠️ 삽입 오류: {e}")

        print(f"  📅 {date_str}: {num_ips}개 IP 생성")

    # 커밋
    conn.commit()

    print(f"\n✅ 총 {total_inserted}개 IP 저장 완료")

    # 통계 확인
    cursor.execute(
        """
        SELECT 
            DATE(detection_date) as date,
            COUNT(*) as count,
            COUNT(DISTINCT ip_address) as unique_ips
        FROM blacklist
        WHERE source LIKE '%TEST%'
        GROUP BY DATE(detection_date)
        ORDER BY date DESC
        LIMIT 7
    """
    )

    print("\n📊 최근 7일 통계:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}개 항목, {row[2]}개 고유 IP")

    # 소스별 통계
    cursor.execute(
        """
        SELECT source, COUNT(*) as count
        FROM blacklist
        WHERE source LIKE '%TEST%'
        GROUP BY source
    """
    )

    print("\n📊 소스별 통계:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}개")

    # 위협 레벨별 통계
    cursor.execute(
        """
        SELECT threat_level, COUNT(*) as count
        FROM blacklist
        WHERE source LIKE '%TEST%'
        GROUP BY threat_level
    """
    )

    print("\n📊 위협 레벨별 통계:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}개")

    conn.close()
    print("\n✅ 테스트 데이터 생성 완료!")

    # API로 데이터 확인
    print("\n🔍 API로 데이터 확인 중...")
    import requests

    try:
        # 수집 상태 확인
        response = requests.get("http://localhost:32542/api/collection/status")
        if response.status_code == 200:
            data = response.json()
            print(f"  활성 IP: {data.get('stats', {}).get('active_ips', 0)}개")
            print(f"  전체 IP: {data.get('stats', {}).get('total_ips', 0)}개")

        # 분석 API 확인
        response = requests.get("http://localhost:32542/api/v2/analytics/summary")
        if response.status_code == 200:
            data = response.json()
            print(f"\n📊 분석 요약:")
            print(f"  전체 IP: {data.get('data', {}).get('total_ips', 0)}개")
            print(f"  활성 IP: {data.get('data', {}).get('active_ips', 0)}개")

    except Exception as e:
        print(f"  ⚠️ API 확인 실패: {e}")


if __name__ == "__main__":
    create_test_data()
