#!/usr/bin/env python3
"""
PostgreSQL 데이터베이스 초기화 스크립트
SQLite 제거 후 PostgreSQL 전용으로 변경
"""
import os
import sys
import logging
import argparse
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.database import DatabaseManager
    from src.config.settings import Settings
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    print("프로젝트 루트 경로를 확인하세요.")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_postgresql_connection(database_url: str) -> bool:
    """PostgreSQL 연결 확인"""
    try:
        import psycopg2
        # URL에서 연결 정보 추출
        if database_url.startswith("postgresql://"):
            conn = psycopg2.connect(database_url)
            conn.close()
            return True
        else:
            logger.error("❌ PostgreSQL URL이 아닙니다")
            return False
    except ImportError:
        logger.error("❌ psycopg2 모듈이 설치되지 않았습니다: pip install psycopg2-binary")
        return False
    except Exception as e:
        logger.error(f"❌ PostgreSQL 연결 실패: {e}")
        return False


def init_postgresql_database(force_recreate=False):
    """PostgreSQL 데이터베이스 초기화"""
    settings = Settings()
    database_url = settings.database_uri
    
    print("🐘 PostgreSQL 데이터베이스 초기화")
    print(f"📋 스키마 버전: 2.0.0 (PostgreSQL)")
    print(f"🔄 강제 재생성: {'예' if force_recreate else '아니오'}")
    print(f"🔗 연결 URL: {database_url.split('@')[0]}@[HIDDEN]")
    
    # PostgreSQL 연결 확인
    if not check_postgresql_connection(database_url):
        print("❌ PostgreSQL 서버에 연결할 수 없습니다")
        print("   Docker Compose를 실행했는지 확인하세요: docker-compose up -d postgresql")
        return False
    
    try:
        # DatabaseManager 인스턴스 생성
        db_manager = DatabaseManager(database_url)
        
        print("🔗 PostgreSQL 연결 성공!")
        
        if force_recreate:
            print("⚠️ 강제 재생성 모드 - 모든 데이터가 삭제됩니다!")
            confirm = input("계속하시겠습니까? (yes/no): ")
            if confirm.lower() != 'yes':
                print("취소되었습니다.")
                return False
            
            # 테이블 삭제 (강제 재생성)
            with db_manager.engine.connect() as conn:
                tables = [
                    'collection_history', 'collection_settings', 'collection_credentials',
                    'collection_sources', 'system_logs', 'cache_entries', 'system_status',
                    'auth_attempts', 'collection_logs', 'metadata', 'blacklist', 'blacklist_entries'
                ]
                for table in tables:
                    try:
                        from sqlalchemy import text
                        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                        conn.commit()
                        logger.info(f"테이블 삭제: {table}")
                    except Exception as e:
                        logger.warning(f"테이블 삭제 실패 {table}: {e}")
        
        # 데이터베이스 초기화
        db_manager.init_db()
        
        print("✅ PostgreSQL 데이터베이스 초기화 성공!")
        
        # 테이블 확인
        with db_manager.engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("""
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = result.fetchall()
            
            print("📊 생성된 테이블:")
            for table_name, table_type in tables:
                print(f"  ✅ {table_name} ({table_type})")
        
        # 기본 메타데이터 삽입
        with db_manager.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO metadata (key, value) VALUES 
                    ('db_version', '2.0'),
                    ('db_type', 'postgresql'),
                    ('initialized_at', CURRENT_TIMESTAMP::text),
                    ('schema_migrated', 'true')
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
            """))
            conn.commit()
            
        print("🎯 메타데이터 초기화 완료")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
        return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='PostgreSQL 데이터베이스 초기화')
    parser.add_argument('--force', action='store_true', help='강제 재생성 (모든 데이터 삭제)')
    parser.add_argument('--check', action='store_true', help='연결 상태만 확인')
    
    args = parser.parse_args()
    
    if args.check:
        settings = Settings()
        if check_postgresql_connection(settings.database_uri):
            print("✅ PostgreSQL 연결 정상")
            return 0
        else:
            print("❌ PostgreSQL 연결 실패")
            return 1
    
    # 환경변수 확인
    database_url = os.getenv("DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql://"):
        print("❌ DATABASE_URL 환경변수가 PostgreSQL URL로 설정되지 않았습니다")
        print("   예: DATABASE_URL=postgresql://user:pass@localhost:5432/dbname")
        return 1
    
    # 데이터베이스 초기화 실행
    success = init_postgresql_database(force_recreate=args.force)
    
    if success:
        print("\n🎉 PostgreSQL 데이터베이스 초기화 완료!")
        print("이제 애플리케이션을 시작할 수 있습니다.")
        return 0
    else:
        print("\n❌ 데이터베이스 초기화 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())