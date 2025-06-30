#!/usr/bin/env python3
"""
통합 블랙리스트 관리 시스템 - 통합 서비스 엔트리 포인트
모든 기능을 하나의 서비스로 통합
"""
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 데이터베이스 스키마 자동 수정
def ensure_database_schema():
    """데이터베이스 스키마 확인 및 수정"""
    import sqlite3
    
    # Docker 환경 우선 경로 설정
    if os.path.exists('/app'):
        # Docker 환경
        db_path = '/app/instance/blacklist.db'
        instance_dir = '/app/instance'
    else:
        # 로컬 개발 환경
        db_path = os.path.join(current_dir, 'instance', 'blacklist.db')
        instance_dir = os.path.join(current_dir, 'instance')
    
    # instance 디렉토리 생성
    os.makedirs(instance_dir, exist_ok=True)
    
    logger.info(f"데이터베이스 스키마 확인 중: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 기본 테이블 생성 (없는 경우)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklist_ip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address VARCHAR(45) NOT NULL,
                source VARCHAR(50) NOT NULL,
                detection_date TIMESTAMP,
                reason TEXT,
                threat_level VARCHAR(20),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # 인덱스 생성
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ip_address ON blacklist_ip(ip_address)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON blacklist_ip(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_active ON blacklist_ip(is_active)")
        
        conn.commit()
        logger.info("✅ 데이터베이스 스키마 확인 완료")
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 오류: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

# 애플리케이션 시작 전 스키마 확인
ensure_database_schema()

# Use app_compact as primary application
try:
    from src.core.app_compact import create_compact_app
    application = create_compact_app()
    logger.info("✅ app_compact 성공적으로 로드됨")
except ImportError as e:
    logger.error(f"❌ app_compact import 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)  # app_compact 실패시 종료 (minimal_app 사용 안함)
except Exception as e:
    logger.error(f"❌ app_compact 생성 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == '__main__':
    import argparse
    from src.config.settings import settings
    
    parser = argparse.ArgumentParser(description='Blacklist Management System')
    parser.add_argument('--port', type=int, default=settings.port, help='Port to run on')
    parser.add_argument('--host', default=settings.host, help='Host to bind to')
    parser.add_argument('--debug', action='store_true', default=settings.debug, help='Enable debug mode')
    
    args = parser.parse_args()
    
    # 설정 검증
    validation = settings.validate()
    if not validation['valid']:
        logger.error(f"Configuration errors: {validation['errors']}")
        sys.exit(1)
    
    if validation['warnings']:
        for warning in validation['warnings']:
            logger.warning(f"Configuration warning: {warning}")
    
    print(f"Starting {settings.app_name} v{settings.app_version} on {args.host}:{args.port}")
    print(f"Environment: {settings.environment}, Debug: {args.debug}")
    
    application.run(host=args.host, port=args.port, debug=args.debug)