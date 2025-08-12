#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
운영/개발 환경 모두에서 사용 가능
"""
import os
import sqlite3
import sys


def init_database(force_recreate=False):
    # DATABASE_URL 환경변수에서 경로 추출 (컨테이너 환경 우선)
    database_url = os.getenv("DATABASE_URL", "sqlite:////app/instance/blacklist.db")
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
    else:
        # Docker 환경과 로컬 환경 모두 지원
        if os.path.exists("/app"):
            db_path = "/app/instance/blacklist.db"
        else:
            db_path = "instance/blacklist.db"
    
    # 데이터베이스 디렉토리 생성
    db_dir = os.path.dirname(db_path)
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Failed to create directory {db_dir}: {e}")

    print(f"Initializing database at: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 기존 테이블 체크
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='blacklist_ip'
        """
        )
        table_exists = cursor.fetchone() is not None

        if table_exists:
            # 테이블이 있으면 컬럼 체크
            cursor.execute("PRAGMA table_info(blacklist_ip)")
            columns = [col[1] for col in cursor.fetchall()]

            if "ip" not in columns or force_recreate:
                if force_recreate:
                    print("🔄 Force recreating table...")
                else:
                    print(
                        "❌ 'ip' column missing in blacklist_ip table. Recreating table..."
                    )
                cursor.execute("DROP TABLE IF EXISTS blacklist_ip")
                table_exists = False

        if not table_exists:
            print("Creating blacklist_ip table...")
            cursor.execute(
                """
            CREATE TABLE blacklist_ip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip VARCHAR(45) UNIQUE NOT NULL,
                ip_address VARCHAR(45),      -- REGTECH 원본 필드
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                detection_date TIMESTAMP,
                reg_date TIMESTAMP,          -- REGTECH 등록일
                attack_type VARCHAR(50),
                reason VARCHAR(200),         -- REGTECH 사유
                country VARCHAR(100),
                threat_level VARCHAR(50),    -- REGTECH 위협 수준
                as_name VARCHAR(200),        -- AS 이름
                city VARCHAR(100),           -- 도시
                source VARCHAR(100),
                is_active BOOLEAN DEFAULT 1, -- IP 활성 상태
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 업데이트 시간
                extra_data TEXT
            )
            """
            )
            cursor.execute("CREATE INDEX idx_blacklist_ip ON blacklist_ip(ip)")
            cursor.execute("CREATE INDEX idx_blacklist_source ON blacklist_ip(source)")

        # ip_detection 테이블
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS ip_detection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip VARCHAR(45) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source VARCHAR(50),
            attack_type VARCHAR(50),
            confidence_score REAL DEFAULT 1.0,
            blacklist_ip_id INTEGER,
            FOREIGN KEY (blacklist_ip_id) REFERENCES blacklist_ip(id)
        )
        """
        )

        # expires_at 컬럼 추가 (이미 있으면 무시)
        try:
            cursor.execute("ALTER TABLE blacklist_ip ADD COLUMN expires_at TIMESTAMP")
            print("✅ Added expires_at column to blacklist_ip table")
        except sqlite3.OperationalError:
            # 컬럼이 이미 존재하면 무시
            pass

        # daily_stats 테이블
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE NOT NULL,
            total_ips INTEGER DEFAULT 0,
            regtech_count INTEGER DEFAULT 0,
            secudium_count INTEGER DEFAULT 0,
            public_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        conn.commit()
        conn.close()

        print("✅ Database initialized successfully!")
        return True

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    # 명령줄 인자로 --force-recreate 옵션 지원
    force_recreate = "--force-recreate" in sys.argv
    success = init_database(force_recreate=force_recreate)
    sys.exit(0 if success else 1)
