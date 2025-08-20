#!/usr/bin/env python3
"""
API 키 관리 모델
"""

import hashlib
import os
import secrets
import sqlite3
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional


@dataclass
class ApiKey:
    """API 키 데이터 모델"""

    key_id: str
    key_hash: str  # 해시된 키
    name: str
    description: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    usage_count: int = 0

    def to_dict(self) -> Dict:
        """딕셔너리로 변환 (보안상 key_hash는 제외)"""
        data = asdict(self)
        data.pop("key_hash", None)  # 보안상 해시 제외
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        data["expires_at"] = self.expires_at.isoformat() if self.expires_at else None
        data["last_used_at"] = (
            self.last_used_at.isoformat() if self.last_used_at else None
        )
        return data

    def is_expired(self) -> bool:
        """만료 여부 확인"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at


class ApiKeyManager:
    """API 키 관리자"""

    def __init__(self, db_path: str = "instance/api_keys.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """데이터베이스 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    description TEXT,
                    permissions TEXT,  -- JSON array as string
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    last_used_at TEXT,
                    usage_count INTEGER NOT NULL DEFAULT 0
                )
            """
            )
            conn.commit()

    def _hash_key(self, api_key: str) -> str:
        """API 키 해시화"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def create_api_key(
        self,
        name: str,
        description: str = "",
        permissions: List[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> tuple[str, ApiKey]:
        """
        새 API 키 생성
        Returns: (원본_키, ApiKey_객체)
        """
        # 고유한 키 생성
        raw_key = "ak_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)
        key_id = secrets.token_hex(16)

        # 만료일 설정
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)

        # 권한 설정
        if permissions is None:
            permissions = ["read"]

        api_key = ApiKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            description=description,
            permissions=permissions,
            created_at=datetime.now(),
            expires_at=expires_at,
        )

        # 데이터베이스에 저장
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO api_keys
                (
                    key_id,
                    key_hash,
                    name,
                    description,
                    permissions,
                    created_at,
                    expires_at,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    api_key.key_id,
                    api_key.key_hash,
                    api_key.name,
                    api_key.description,
                    ",".join(api_key.permissions),
                    api_key.created_at.isoformat(),
                    api_key.expires_at.isoformat() if api_key.expires_at else None,
                    api_key.is_active,
                ),
            )
            conn.commit()

        return raw_key, api_key

    def validate_api_key(self, api_key: str) -> Optional[ApiKey]:
        """API 키 검증 및 사용 정보 업데이트"""
        if not api_key:
            return None

        key_hash = self._hash_key(api_key)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT key_id, key_hash, name, description, permissions,
                       created_at, expires_at, is_active, last_used_at, usage_count
                FROM api_keys
                WHERE key_hash = ? AND is_active = 1
            """,
                (key_hash,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            # ApiKey 객체 생성
            api_key_obj = ApiKey(
                key_id=row[0],
                key_hash=row[1],
                name=row[2],
                description=row[3],
                permissions=row[4].split(",") if row[4] else [],
                created_at=datetime.fromisoformat(row[5]),
                expires_at=datetime.fromisoformat(row[6]) if row[6] else None,
                is_active=bool(row[7]),
                last_used_at=datetime.fromisoformat(row[8]) if row[8] else None,
                usage_count=row[9],
            )

            # 만료 확인
            if api_key_obj.is_expired():
                return None

            # 사용 정보 업데이트
            current_time = datetime.now()
            conn.execute(
                """
                UPDATE api_keys
                SET last_used_at = ?, usage_count = usage_count + 1
                WHERE key_id = ?
            """,
                (current_time.isoformat(), api_key_obj.key_id),
            )
            conn.commit()

            # 업데이트된 정보로 객체 갱신
            api_key_obj.last_used_at = current_time
            api_key_obj.usage_count += 1

            return api_key_obj

    def list_api_keys(self, include_inactive: bool = False) -> List[ApiKey]:
        """API 키 목록 조회"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT key_id, key_hash, name, description, permissions,
                       created_at, expires_at, is_active, last_used_at, usage_count
                FROM api_keys
            """
            if not include_inactive:
                query += " WHERE is_active = 1"

            cursor = conn.execute(query + " ORDER BY created_at DESC")

            api_keys = []
            for row in cursor.fetchall():
                api_key = ApiKey(
                    key_id=row[0],
                    key_hash=row[1],
                    name=row[2],
                    description=row[3],
                    permissions=row[4].split(",") if row[4] else [],
                    created_at=datetime.fromisoformat(row[5]),
                    expires_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    is_active=bool(row[7]),
                    last_used_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    usage_count=row[9],
                )
                api_keys.append(api_key)

            return api_keys

    def revoke_api_key(self, key_id: str) -> bool:
        """API 키 비활성화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE api_keys SET is_active = 0 WHERE key_id = ?
            """,
                (key_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_api_key(self, key_id: str) -> bool:
        """API 키 완전 삭제"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM api_keys WHERE key_id = ?
            """,
                (key_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_api_key(self, key_id: str) -> Optional[ApiKey]:
        """특정 API 키 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT key_id, key_hash, name, description, permissions,
                       created_at, expires_at, is_active, last_used_at, usage_count
                FROM api_keys
                WHERE key_id = ?
            """,
                (key_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return ApiKey(
                key_id=row[0],
                key_hash=row[1],
                name=row[2],
                description=row[3],
                permissions=row[4].split(",") if row[4] else [],
                created_at=datetime.fromisoformat(row[5]),
                expires_at=datetime.fromisoformat(row[6]) if row[6] else None,
                is_active=bool(row[7]),
                last_used_at=datetime.fromisoformat(row[8]) if row[8] else None,
                usage_count=row[9],
            )


# 전역 인스턴스
_api_key_manager = None


def get_api_key_manager() -> ApiKeyManager:
    """전역 API 키 매니저 인스턴스 반환"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = ApiKeyManager()
    return _api_key_manager
