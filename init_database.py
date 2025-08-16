#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트 - 향상된 스키마 관리
운영/개발 환경 모두에서 사용 가능
"""
import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가 (현재 위치가 프로젝트 루트)
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.core.database import initialize_database, get_database_schema
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    print("대안 임포트 시도 중...")
    try:
        from src.core.database_schema import initialize_database, get_database_schema
    except ImportError:
        print("❌ 대안 임포트도 실패했습니다. database 모듈을 확인하세요.")
        sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_path() -> str:
    """데이터베이스 경로 결정"""
    # DATABASE_URL 환경변수에서 경로 추출 (컨테이너 환경 우선)
    database_url = os.getenv("DATABASE_URL", "sqlite:///instance/blacklist.db")
    
    if database_url.startswith("sqlite:///"):
        # Handle local relative paths
        if database_url.startswith("sqlite:///./"):
            db_path = database_url[12:]  # Remove 'sqlite:///./'
        else:
            db_path = database_url[10:]  # Remove 'sqlite:///'
    else:
        # Default fallback
        db_path = "instance/blacklist.db"
    
    return db_path


def init_database_enhanced(force_recreate=False, migrate=True):
    """향상된 데이터베이스 초기화"""
    db_path = get_database_path()
    database_url = os.getenv("DATABASE_URL", "sqlite:///instance/blacklist.db")
    
    print(f"🔧 데이터베이스 초기화 중: {db_path}")
    print(f"📋 스키마 버전: 2.0.0")
    print(f"🔄 강제 재생성: {'예' if force_recreate else '아니오'}")
    print(f"🔄 자동 마이그레이션: {'예' if migrate else '아니오'}")
    
    try:
        # 스키마 인스턴스 생성 (database_url 사용)
        schema = get_database_schema(database_url)
        
        # 현재 스키마 버전 확인
        current_version = schema.get_current_schema_version()
        if current_version:
            print(f"📊 현재 스키마 버전: {current_version}")
        else:
            print("📊 새로운 데이터베이스 설치")
        
        # 강제 재생성 처리
        if force_recreate:
            db_file = Path(db_path)
            if db_file.exists():
                db_file.unlink()
                print("🗑️ 기존 데이터베이스 파일 삭제됨")
        
        # 데이터베이스 초기화
        success = initialize_database(db_path, force_recreate)
        
        if success:
            print("✅ 데이터베이스 초기화 성공!")
            
            # 테이블 통계 출력
            stats = schema.get_table_stats()
            print("📊 테이블 통계:")
            for table, stat in stats.items():
                if "error" in stat:
                    print(f"  ❌ {table}: {stat['error']}")
                else:
                    print(f"  ✅ {table}: {stat['count']}개 레코드")
            
            # 마이그레이션 실행
            if migrate and not force_recreate:
                print("🔄 스키마 마이그레이션 확인 중...")
                migration_success = schema.migrate_schema()
                if migration_success:
                    print("✅ 마이그레이션 완료")
                else:
                    print("⚠️ 마이그레이션 실패 또는 불필요")
            
            # 최종 버전 확인
            final_version = schema.get_current_schema_version()
            print(f"🎯 최종 스키마 버전: {final_version}")
            
            return True
        else:
            print("❌ 데이터베이스 초기화 실패!")
            return False
            
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 중 오류: {e}")
        logger.exception("데이터베이스 초기화 실패")
        return False


def legacy_init_database(force_recreate=False):
    """레거시 데이터베이스 초기화 (호환성 유지)"""
    print("⚠️ 레거시 모드로 데이터베이스 초기화 중...")
    
    # 기존 코드 유지 (원래 init_database 함수 내용)
    database_url = os.getenv("DATABASE_URL", "sqlite:////app/instance/blacklist.db")
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
    else:
        if os.path.exists("/app"):
            db_path = "/app/instance/blacklist.db"
        else:
            db_path = "instance/blacklist.db"
    
    db_dir = os.path.dirname(db_path)
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Failed to create directory {db_dir}: {e}")

    print(f"Initializing database at: {db_path}")

    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 기존 테이블 체크 (올바른 테이블명 사용)
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='blacklist_entries'
        """
        )
        table_exists = cursor.fetchone() is not None

        if table_exists:
            cursor.execute("PRAGMA table_info(blacklist_entries)")
            columns = [col[1] for col in cursor.fetchall()]

            if "ip_address" not in columns or force_recreate:
                if force_recreate:
                    print("🔄 Force recreating table...")
                else:
                    print("❌ 'ip_address' column missing in blacklist_entries table. Recreating table...")
                cursor.execute("DROP TABLE IF EXISTS blacklist_entries")
                table_exists = False

        if not table_exists:
            print("Creating blacklist_entries table...")
            cursor.execute(
                """
            CREATE TABLE blacklist_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL UNIQUE,
                first_seen TEXT,
                last_seen TEXT,
                detection_months TEXT,
                is_active BOOLEAN DEFAULT 1,
                days_until_expiry INTEGER DEFAULT 90,
                threat_level TEXT DEFAULT 'medium',
                source TEXT NOT NULL DEFAULT 'unknown',
                source_details TEXT,
                country TEXT,
                reason TEXT,
                reg_date TEXT,
                exp_date TEXT,
                view_count INTEGER DEFAULT 0,
                uuid TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                severity_score REAL DEFAULT 0.0,
                confidence_level REAL DEFAULT 1.0,
                tags TEXT,
                last_verified TIMESTAMP,
                verification_status TEXT DEFAULT 'unverified'
            )
            """
            )
            cursor.execute("CREATE INDEX idx_blacklist_entries_ip ON blacklist_entries(ip_address)")
            cursor.execute("CREATE INDEX idx_blacklist_entries_source ON blacklist_entries(source)")

        # collection_logs 테이블 (완전한 스키마)
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS collection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            items_collected INTEGER DEFAULT 0,
            items_new INTEGER DEFAULT 0,
            items_updated INTEGER DEFAULT 0,
            items_failed INTEGER DEFAULT 0,
            execution_time_ms REAL DEFAULT 0.0,
            error_message TEXT,
            details TEXT,
            collection_type TEXT DEFAULT 'scheduled',
            user_id TEXT,
            session_id TEXT,
            data_size_bytes INTEGER DEFAULT 0,
            memory_usage_mb REAL DEFAULT 0.0
        )
        """
        )

        # 추가 테이블들
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            value_type TEXT DEFAULT 'string',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT DEFAULT 'general',
            is_sensitive BOOLEAN DEFAULT 0,
            requires_restart BOOLEAN DEFAULT 0
        )
        """
        )

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


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='데이터베이스 초기화 도구')
    parser.add_argument('--force', '--force-recreate', action='store_true',
                      help='기존 데이터베이스를 강제로 재생성')
    parser.add_argument('--legacy', action='store_true',
                      help='레거시 모드로 초기화 (호환성)')
    parser.add_argument('--no-migrate', action='store_true',
                      help='자동 마이그레이션 비활성화')
    
    args = parser.parse_args()
    
    print("🚀 블랙리스트 데이터베이스 초기화 도구 v2.0")
    print("=" * 50)
    
    if args.legacy:
        success = legacy_init_database(force_recreate=args.force)
    else:
        success = init_database_enhanced(
            force_recreate=args.force,
            migrate=not args.no_migrate
        )
    
    if success:
        print("🎉 데이터베이스 초기화가 완료되었습니다!")
    else:
        print("💥 데이터베이스 초기화에 실패했습니다.")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
