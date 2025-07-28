#!/usr/bin/env python3
"""
블랙리스트 만료 기능 추가 스크립트
- expires_at 컬럼 추가 (등록일 + 3개월)
- 활성/만료 상태 관리
- 통계 기능 개선
"""
import os
import sqlite3
from datetime import datetime, timedelta

# Docker 환경
db_path = (
    '/app/instance/blacklist.db' if os.path.exists('/app') else 'instance/blacklist.db'
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
    if 'detection_date' not in columns:
        print("🔧 detection_date 컬럼 추가 중...")
        cursor.execute(
            """
            ALTER TABLE blacklist_ip 
            ADD COLUMN detection_date TIMESTAMP
        """
        )
        print("✅ detection_date 컬럼 추가 완료")

    # 3. expires_at 컬럼이 없으면 추가
    if 'expires_at' not in columns:
        print("🔧 expires_at 컬럼 추가 중...")
        cursor.execute(
            """
            ALTER TABLE blacklist_ip 
            ADD COLUMN expires_at TIMESTAMP
        """
        )
        print("✅ expires_at 컬럼 추가 완료")

    # 4. is_active 컬럼이 없으면 추가 (만료되지 않은 활성 IP 표시)
    if 'is_active' not in columns:
        print("🔧 is_active 컬럼 추가 중...")
        cursor.execute(
            """
            ALTER TABLE blacklist_ip 
            ADD COLUMN is_active BOOLEAN DEFAULT 1
        """
        )
        print("✅ is_active 컬럼 추가 완료")

    # 5. 기존 데이터의 detection_date를 created_at으로 설정
    cursor.execute(
        """
        UPDATE blacklist_ip 
        SET detection_date = created_at 
        WHERE detection_date IS NULL
    """
    )
    updated = cursor.rowcount
    print(f"✅ {updated}개 레코드의 detection_date 업데이트 완료")

    # 6. expires_at 설정 (detection_date + 3개월)
    cursor.execute(
        """
        UPDATE blacklist_ip 
        SET expires_at = datetime(detection_date, '+3 months')
        WHERE expires_at IS NULL AND detection_date IS NOT NULL
    """
    )
    updated = cursor.rowcount
    print(f"✅ {updated}개 레코드의 expires_at 업데이트 완료")

    # 7. is_active 상태 업데이트 (현재 시점 기준)
    cursor.execute(
        """
        UPDATE blacklist_ip 
        SET is_active = CASE 
            WHEN expires_at > datetime('now') THEN 1 
            ELSE 0 
        END
        WHERE expires_at IS NOT NULL
    """
    )
    updated = cursor.rowcount
    print(f"✅ {updated}개 레코드의 활성 상태 업데이트 완료")

    # 8. 현재 활성/만료 통계
    cursor.execute(
        """
        SELECT 
            is_active,
            COUNT(DISTINCT ip) as count,
            COUNT(DISTINCT ip) * 100.0 / (SELECT COUNT(DISTINCT ip) FROM blacklist_ip) as percentage
        FROM blacklist_ip 
        GROUP BY is_active
    """
    )

    print("\n📊 활성/만료 상태 통계:")
    print("상태    | IP 수    | 비율")
    print("-" * 30)
    for row in cursor.fetchall():
        is_active, count, percentage = row
        status = "활성" if is_active else "만료"
        print(f"{status:6} | {count:,}개 | {percentage:.1f}%")

    # 9. 월별 활성 IP 통계
    cursor.execute(
        """
        SELECT 
            strftime('%Y-%m', detection_date) as month,
            source,
            COUNT(DISTINCT ip) as total_ips,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_ips
        FROM blacklist_ip 
        WHERE detection_date IS NOT NULL
        GROUP BY month, source
        ORDER BY month, source
    """
    )

    print("\n📊 월별 소스별 IP 통계 (활성/전체):")
    print("월     | 소스       | 활성 IP | 전체 IP")
    print("-" * 45)
    for row in cursor.fetchall():
        month, source, total, active = row
        print(f"{month} | {source:10} | {active:,}개 | {total:,}개")

    # 10. 만료 예정 통계 (향후 30일)
    cursor.execute(
        """
        SELECT 
            COUNT(DISTINCT ip) as expiring_count
        FROM blacklist_ip 
        WHERE is_active = 1 
        AND expires_at BETWEEN datetime('now') AND datetime('now', '+30 days')
    """
    )

    expiring_count = cursor.fetchone()[0]
    print(f"\n⏰ 향후 30일 내 만료 예정: {expiring_count:,}개")

    conn.commit()
    conn.close()

    print("\n✅ 블랙리스트 만료 기능 추가 완료!")
    print("📝 추가된 기능:")
    print("   - 등록일 기반 자동 만료 (3개월)")
    print("   - 활성/만료 상태 관리")
    print("   - 만료 기반 통계")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    if conn:
        conn.rollback()
        conn.close()
