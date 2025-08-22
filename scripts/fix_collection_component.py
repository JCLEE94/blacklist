#!/usr/bin/env python3
"""
수집 컴포넌트 강제 초기화 및 활성화
"""

import os
import sys
import sqlite3
from datetime import datetime

# 프로젝트 경로 추가
sys.path.insert(0, "/home/jclee/app/blacklist")


def initialize_collection_components():
    """수집 컴포넌트 초기화"""
    print("=" * 60)
    print("수집 컴포넌트 강제 초기화")
    print("=" * 60)

    # 1. 환경 변수 설정
    print("\n1️⃣ 환경 변수 설정...")
    os.environ["REGTECH_USERNAME"] = "nextrade"
    os.environ["REGTECH_PASSWORD"] = "Sprtmxm1@3"
    os.environ["COLLECTION_ENABLED"] = "true"
    os.environ["FORCE_DISABLE_COLLECTION"] = "false"

    # 2. 데이터베이스 확인 및 설정
    print("\n2️⃣ 데이터베이스 설정...")

    # SQLite 데이터베이스 경로
    db_paths = [
        "instance/blacklist.db",
        "config/data/blacklist.db",
        "/app/instance/blacklist.db",
    ]

    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            print(f"   ✅ 데이터베이스 발견: {path}")
            break

    if not db_path:
        # 새 데이터베이스 생성
        db_path = "instance/blacklist.db"
        os.makedirs("instance", exist_ok=True)
        print(f"   📁 새 데이터베이스 생성: {db_path}")

    # 데이터베이스 초기화
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 필요한 테이블 생성
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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS collection_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # 수집 설정 활성화
    cursor.execute(
        """
        INSERT OR REPLACE INTO collection_settings (setting_key, setting_value, updated_at)
        VALUES ('collection_enabled', 'true', CURRENT_TIMESTAMP)
    """
    )

    cursor.execute(
        """
        INSERT OR REPLACE INTO collection_settings (setting_key, setting_value, updated_at)
        VALUES ('regtech_enabled', 'true', CURRENT_TIMESTAMP)
    """
    )

    cursor.execute(
        """
        INSERT OR REPLACE INTO collection_settings (setting_key, setting_value, updated_at)
        VALUES ('regtech_username', 'nextrade', CURRENT_TIMESTAMP)
    """
    )

    conn.commit()
    print("   ✅ 데이터베이스 초기화 완료")

    # 3. 수집 컴포넌트 직접 임포트 및 초기화
    print("\n3️⃣ 수집 컴포넌트 초기화...")

    try:
        # CollectionManager 초기화
        from src.core.managers.collection_manager import CollectionManager

        collection_manager = CollectionManager()
        print(f"   ✅ CollectionManager 초기화 성공")
        print(f"   - 수집 활성화: {collection_manager.collection_enabled}")
        print(f"   - 컴포넌트: {list(collection_manager._components.keys())}")

        # 컴포넌트 강제 활성화
        if not collection_manager._components:
            print("\n   ⚠️ 컴포넌트가 없음 - 수동 초기화 시도...")

            # REGTECH 컴포넌트 직접 생성
            try:
                from src.core.collectors.regtech_collector import REGTECHCollector

                regtech = REGTECHCollector(username="nextrade", password="Sprtmxm1@3")

                collection_manager._components["regtech"] = regtech
                print("   ✅ REGTECH 컴포넌트 수동 초기화 성공")

            except Exception as e:
                print(f"   ❌ REGTECH 초기화 실패: {e}")

        # 수집 활성화
        collection_manager.collection_enabled = True
        collection_manager.daily_collection_enabled = True

        print(f"\n   최종 상태:")
        print(f"   - 수집 활성화: {collection_manager.collection_enabled}")
        print(f"   - 일일 수집: {collection_manager.daily_collection_enabled}")
        print(f"   - 컴포넌트: {list(collection_manager._components.keys())}")

    except Exception as e:
        print(f"   ❌ CollectionManager 초기화 실패: {e}")

    # 4. UnifiedService 확인
    print("\n4️⃣ UnifiedService 초기화...")

    try:
        from src.core.services.unified_service_factory import get_unified_service

        service = get_unified_service()
        print(f"   ✅ UnifiedService 초기화 성공")

        # 수집 활성화
        result = service.enable_collection()
        print(f"   수집 활성화 결과: {result}")

        # 상태 확인
        status = service.get_collection_status()
        print(f"\n   수집 상태:")
        print(f"   - 활성화: {status.get('collection_enabled')}")
        print(f"   - 소스: {status.get('sources', {})}")

        # REGTECH 수집 트리거
        if "regtech" in service._components:
            print("\n5️⃣ REGTECH 수집 테스트...")
            trigger_result = service.trigger_regtech_collection(force=True)
            print(f"   결과: {trigger_result}")
        else:
            print("\n   ⚠️ REGTECH 컴포넌트를 찾을 수 없음")

    except Exception as e:
        print(f"   ❌ UnifiedService 초기화 실패: {e}")

    conn.close()
    print("\n" + "=" * 60)
    print("초기화 완료")
    print("=" * 60)


def test_collection_api():
    """API를 통한 수집 테스트"""
    print("\n6️⃣ API 테스트...")

    import requests

    # 수집 활성화
    try:
        response = requests.post("http://localhost:32542/api/collection/enable")
        print(f"   수집 활성화: {response.status_code}")
        if response.status_code == 200:
            print(f"   응답: {response.json()}")
    except Exception as e:
        print(f"   ❌ API 오류: {e}")

    # REGTECH 수집 트리거
    try:
        response = requests.post(
            "http://localhost:32542/api/collection/regtech/trigger"
        )
        print(f"\n   REGTECH 트리거: {response.status_code}")
        if response.status_code == 200:
            print(f"   응답: {response.json()}")
    except Exception as e:
        print(f"   ❌ API 오류: {e}")

    # 상태 확인
    try:
        response = requests.get("http://localhost:32542/api/collection/status")
        print(f"\n   수집 상태: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   - 수집 활성화: {data.get('collection_enabled')}")
            print(f"   - REGTECH: {data.get('sources', {}).get('regtech', {})}")
    except Exception as e:
        print(f"   ❌ API 오류: {e}")


if __name__ == "__main__":
    initialize_collection_components()
    test_collection_api()
