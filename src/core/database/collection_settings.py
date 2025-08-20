#!/usr/bin/env python3
"""
수집 설정 데이터베이스 모델
UI에서 저장한 설정을 DB에 저장하고 수집기가 활용
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from cryptography.fernet import Fernet


class CollectionSettingsDB:
    """수집 설정 데이터베이스 관리 클래스"""

    def __init__(self, db_path: str = "instance/blacklist.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)

        # 암호화 키 초기화
        self.cipher_key = self._get_or_create_cipher_key()
        self.cipher = Fernet(self.cipher_key)

        # 테이블 초기화
        self._init_tables()

    def _get_or_create_cipher_key(self) -> bytes:
        """암호화 키 생성 또는 로드"""
        key_file = self.db_path.parent / ".settings_key"
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)
            return key

    def _init_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            # 수집 소스 설정 테이블
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    base_url TEXT NOT NULL,
                    config_json TEXT,  -- 암호화된 설정
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 자격증명 테이블
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_encrypted TEXT NOT NULL,  -- 암호화된 패스워드
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_name) REFERENCES collection_sources (name)
                )
            """
            )

            # 수집 설정 테이블
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 수집 이력 테이블
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    success BOOLEAN DEFAULT 0,
                    collected_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT  -- 추가 메타데이터
                )
            """
            )

            # 인덱스 생성
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_collection_history_source ON collection_history(source_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_collection_history_date ON collection_history(collected_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_collection_credentials_source ON collection_credentials(source_name)"
            )

            conn.commit()

    def save_source_config(
        self,
        name: str,
        display_name: str,
        base_url: str,
        config: Dict[str, Any],
        enabled: bool = True,
    ) -> bool:
        """수집 소스 설정 저장"""
        try:
            # 설정을 암호화
            config_encrypted = self.cipher.encrypt(json.dumps(config).encode()).decode()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO collection_sources 
                    (name, display_name, enabled, base_url, config_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        name,
                        display_name,
                        enabled,
                        base_url,
                        config_encrypted,
                        datetime.now(),
                    ),
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"소스 설정 저장 실패: {e}")
            return False

    def get_source_config(self, name: str) -> Optional[Dict[str, Any]]:
        """수집 소스 설정 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM collection_sources WHERE name = ? AND enabled = 1
                """,
                    (name,),
                )
                row = cursor.fetchone()

                if row:
                    # 암호화된 설정 복호화
                    config_encrypted = row["config_json"]
                    if config_encrypted:
                        config_decrypted = self.cipher.decrypt(
                            config_encrypted.encode()
                        ).decode()
                        config = json.loads(config_decrypted)
                    else:
                        config = {}

                    return {
                        "name": row["name"],
                        "display_name": row["display_name"],
                        "enabled": bool(row["enabled"]),
                        "base_url": row["base_url"],
                        "config": config,
                    }

            return None

        except Exception as e:
            print(f"소스 설정 조회 실패: {e}")
            return None

    def get_all_sources(self) -> List[Dict[str, Any]]:
        """모든 수집 소스 목록 조회"""
        sources = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT name, display_name, enabled, base_url, created_at, updated_at
                    FROM collection_sources
                    ORDER BY created_at
                """
                )

                for row in cursor.fetchall():
                    sources.append(
                        {
                            "name": row["name"],
                            "display_name": row["display_name"],
                            "enabled": bool(row["enabled"]),
                            "base_url": row["base_url"],
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        }
                    )

        except Exception as e:
            print(f"소스 목록 조회 실패: {e}")

        return sources

    def save_credentials(self, source_name: str, username: str, password: str) -> bool:
        """자격증명 저장"""
        try:
            # 패스워드 암호화
            password_encrypted = self.cipher.encrypt(password.encode()).decode()

            with sqlite3.connect(self.db_path) as conn:
                # 기존 자격증명 삭제
                conn.execute(
                    "DELETE FROM collection_credentials WHERE source_name = ?",
                    (source_name,),
                )

                # 새 자격증명 저장
                conn.execute(
                    """
                    INSERT INTO collection_credentials 
                    (source_name, username, password_encrypted, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        source_name,
                        username,
                        password_encrypted,
                        datetime.now(),
                        datetime.now(),
                    ),
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"자격증명 저장 실패: {e}")
            return False

    def get_credentials(self, source_name: str) -> Optional[Dict[str, str]]:
        """자격증명 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT username, password_encrypted 
                    FROM collection_credentials 
                    WHERE source_name = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    (source_name,),
                )
                row = cursor.fetchone()

                if row:
                    # 패스워드 복호화
                    password = self.cipher.decrypt(
                        row["password_encrypted"].encode()
                    ).decode()
                    return {"username": row["username"], "password": password}

            return None

        except Exception as e:
            print(f"자격증명 조회 실패: {e}")
            return None

    def save_setting(self, key: str, value: Any, description: str = "") -> bool:
        """일반 설정 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO collection_settings 
                    (setting_key, setting_value, description, updated_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (key, json.dumps(value), description, datetime.now()),
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"설정 저장 실패: {e}")
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """일반 설정 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT setting_value FROM collection_settings WHERE setting_key = ?
                """,
                    (key,),
                )
                row = cursor.fetchone()

                if row:
                    return json.loads(row[0])

                return default

        except Exception as e:
            print(f"설정 조회 실패: {e}")
            return default

    def save_collection_result(
        self,
        source_name: str,
        start_date: str,
        end_date: str,
        success: bool,
        collected_count: int = 0,
        error_message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """수집 결과 저장"""
        try:
            metadata_json = json.dumps(metadata or {})

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO collection_history 
                    (source_name, start_date, end_date, success, collected_count, 
                     error_message, collected_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        source_name,
                        start_date,
                        end_date,
                        success,
                        collected_count,
                        error_message,
                        datetime.now(),
                        metadata_json,
                    ),
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"수집 결과 저장 실패: {e}")
            return False

    def get_collection_statistics(self) -> Dict[str, Any]:
        """수집 통계 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # 전체 통계
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_collections,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_collections,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_collections,
                        SUM(CASE WHEN success = 1 THEN collected_count ELSE 0 END) as total_ips_collected
                    FROM collection_history
                """
                )
                stats = cursor.fetchone()

                # 소스별 통계
                cursor = conn.execute(
                    """
                    SELECT 
                        source_name,
                        COUNT(*) as total,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN success = 1 THEN collected_count ELSE 0 END) as total_ips
                    FROM collection_history
                    GROUP BY source_name
                """
                )
                sources = {row["source_name"]: dict(row) for row in cursor.fetchall()}

                # 최근 수집
                cursor = conn.execute(
                    """
                    SELECT * FROM collection_history
                    ORDER BY collected_at DESC
                    LIMIT 10
                """
                )
                recent = [dict(row) for row in cursor.fetchall()]

                return {
                    "total_collections": stats["total_collections"] or 0,
                    "successful_collections": stats["successful_collections"] or 0,
                    "failed_collections": stats["failed_collections"] or 0,
                    "total_ips_collected": stats["total_ips_collected"] or 0,
                    "sources": sources,
                    "recent_collections": recent,
                }

        except Exception as e:
            print(f"통계 조회 실패: {e}")
            return {
                "total_collections": 0,
                "successful_collections": 0,
                "failed_collections": 0,
                "total_ips_collected": 0,
                "sources": {},
                "recent_collections": [],
            }

    def get_collection_calendar(self, year: int, month: int) -> Dict[str, Any]:
        """특정 월의 수집 캘린더 데이터"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # 해당 월 데이터 조회
                cursor = conn.execute(
                    """
                    SELECT 
                        DATE(collected_at) as collection_date,
                        SUM(CASE WHEN success = 1 THEN collected_count ELSE 0 END) as total_ips,
                        COUNT(*) as total_attempts,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts,
                        GROUP_CONCAT(DISTINCT source_name) as sources
                    FROM collection_history
                    WHERE strftime('%Y', collected_at) = ? AND strftime('%m', collected_at) = ?
                    GROUP BY DATE(collected_at)
                """,
                    (str(year), str(month).zfill(2)),
                )

                calendar_data = {}

                # 해당 월의 모든 날짜 초기화
                from datetime import datetime
                from datetime import timedelta

                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(days=1)

                current = start_date
                while current <= end_date:
                    date_str = current.strftime("%Y-%m-%d")
                    calendar_data[date_str] = {
                        "collected": False,
                        "count": 0,
                        "sources": [],
                    }
                    current += timedelta(days=1)

                # 실제 수집 데이터 반영
                for row in cursor.fetchall():
                    date_str = row["collection_date"]
                    if date_str in calendar_data:
                        calendar_data[date_str] = {
                            "collected": row["successful_attempts"] > 0,
                            "count": row["total_ips"] or 0,
                            "sources": (
                                row["sources"].split(",") if row["sources"] else []
                            ),
                        }

                return {
                    "year": year,
                    "month": month,
                    "calendar": calendar_data,
                    "summary": {
                        "total_days": len(calendar_data),
                        "collected_days": sum(
                            1 for d in calendar_data.values() if d["collected"]
                        ),
                        "total_ips": sum(d["count"] for d in calendar_data.values()),
                    },
                }

        except Exception as e:
            print(f"캘린더 조회 실패: {e}")
            return {"year": year, "month": month, "calendar": {}, "summary": {}}


# 테스트 코드
if __name__ == "__main__":
    print("=" * 60)
    print("수집 설정 데이터베이스 테스트")
    print("=" * 60)

    # DB 초기화
    db = CollectionSettingsDB()

    # 1. 소스 설정 저장
    print("\n1. 소스 설정 저장")
    regtech_config = {
        "endpoints": {
            "login": "/login/loginForm",
            "login_action": "/login/loginAction",
            "search": "/mipam/miPamBoard013.do",
        },
        "timeout": 30,
        "headers": {"User-Agent": "Mozilla/5.0"},
    }

    success = db.save_source_config(
        name="regtech",
        display_name="REGTECH 위협정보",
        base_url="https://regtech.fsec.or.kr",
        config=regtech_config,
        enabled=True,
    )
    print(f"REGTECH 설정 저장: {'✅' if success else '❌'}")

    # 2. 자격증명 저장
    print("\n2. 자격증명 저장")
    success = db.save_credentials("regtech", "regtech", "Sprtmxm1@3")
    print(f"자격증명 저장: {'✅' if success else '❌'}")

    # 3. 설정 조회
    print("\n3. 설정 조회")
    source_config = db.get_source_config("regtech")
    if source_config:
        print(f"소스: {source_config['display_name']}")
        print(f"URL: {source_config['base_url']}")
        print(f"활성화: {source_config['enabled']}")

    creds = db.get_credentials("regtech")
    if creds:
        print(f"사용자: {creds['username']}")
        print(f"패스워드: {'*' * len(creds['password'])}")

    # 4. 수집 결과 저장 테스트
    print("\n4. 수집 결과 저장")
    success = db.save_collection_result(
        source_name="regtech",
        start_date="2025-08-11",
        end_date="2025-08-18",
        success=True,
        collected_count=150,
        error_message="",
        metadata={"test": True},
    )
    print(f"수집 결과 저장: {'✅' if success else '❌'}")

    # 5. 통계 조회
    print("\n5. 통계 조회")
    stats = db.get_collection_statistics()
    print(f"전체 수집: {stats['total_collections']}회")
    print(f"성공: {stats['successful_collections']}회")
    print(f"총 IP: {stats['total_ips_collected']}개")
    print("\n✅ 데이터베이스 테스트 완료")
