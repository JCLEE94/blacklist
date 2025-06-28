#!/usr/bin/env python3
"""
만료 시스템 테스트용 데이터 생성
일부 IP의 등록일을 과거로 설정하여 만료 기능 테스트
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

# Docker 환경
db_path = '/app/instance/blacklist.db' if os.path.exists('/app') else 'instance/blacklist.db'

print(f"📍 DB 경로: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 현재 IP 중 일부를 무작위로 선택하여 과거 날짜로 설정
    cursor.execute("SELECT id, ip FROM blacklist_ip ORDER BY RANDOM() LIMIT 500")
    test_ips = cursor.fetchall()
    
    print(f"🎯 {len(test_ips)}개 IP를 테스트용으로 과거 날짜로 설정...")
    
    updated_count = 0
    
    for ip_id, ip in test_ips:
        # 과거 1-6개월 사이의 무작위 날짜 생성
        days_ago = random.randint(30, 180)  # 1-6개월 전
        past_date = datetime.now() - timedelta(days=days_ago)
        expires_date = past_date + timedelta(days=90)  # 등록일 + 3개월
        
        # detection_date와 expires_at 업데이트
        cursor.execute("""
            UPDATE blacklist_ip 
            SET detection_date = ?, 
                expires_at = ?,
                is_active = CASE 
                    WHEN ? > datetime('now') THEN 1 
                    ELSE 0 
                END
            WHERE id = ?
        """, (
            past_date.strftime('%Y-%m-%d %H:%M:%S'),
            expires_date.strftime('%Y-%m-%d %H:%M:%S'),
            expires_date.strftime('%Y-%m-%d %H:%M:%S'),
            ip_id
        ))
        updated_count += 1
    
    print(f"✅ {updated_count}개 IP의 등록일을 과거로 설정 완료")
    
    # 2. 현재 상태 확인
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_count,
            COUNT(CASE WHEN is_active = 0 THEN 1 END) as expired_count,
            COUNT(*) as total_count
        FROM blacklist_ip
    """)
    
    active, expired, total = cursor.fetchone()
    print(f"\n📊 업데이트 후 상태:")
    print(f"   활성 IP: {active:,}개")
    print(f"   만료 IP: {expired:,}개")
    print(f"   전체 IP: {total:,}개")
    
    # 3. 월별 분포 확인
    cursor.execute("""
        SELECT 
            strftime('%Y-%m', detection_date) as month,
            COUNT(DISTINCT ip) as total_ips,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_ips,
            SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as expired_ips
        FROM blacklist_ip 
        GROUP BY month
        ORDER BY month
    """)
    
    print(f"\n📅 월별 IP 분포 (활성/만료):")
    print("월     | 전체    | 활성    | 만료")
    print("-" * 40)
    for row in cursor.fetchall():
        month, total, active, expired = row
        print(f"{month} | {total:,}개 | {active:,}개 | {expired:,}개")
    
    # 4. 향후 30일 내 만료 예정 확인
    cursor.execute("""
        SELECT COUNT(DISTINCT ip) as expiring_count
        FROM blacklist_ip 
        WHERE is_active = 1 
        AND expires_at BETWEEN datetime('now') AND datetime('now', '+30 days')
    """)
    
    expiring_count = cursor.fetchone()[0]
    print(f"\n⏰ 향후 30일 내 만료 예정: {expiring_count:,}개")
    
    conn.commit()
    conn.close()
    
    print("\n✅ 테스트용 만료 데이터 생성 완료!")
    print("📝 이제 대시보드에서 만료 기능을 테스트할 수 있습니다.")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    if conn:
        conn.rollback()
        conn.close()