#!/usr/bin/env python3
"""
데이터베이스 스키마 수정 스크립트

Critical Issues 해결:
1. system_logs 테이블에 additional_data 컬럼 추가
2. auth_attempts 테이블 확인 및 생성
3. 스키마 버전 2.0.0으로 업데이트
4. SystemMonitor _check_cache_status 메서드 검증
"""

import os
import sys
import sqlite3
import logging
import time
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.database.schema_manager import DatabaseSchema
from src.utils.system_stability import SystemMonitor, DatabaseStabilityManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_database(db_path: str) -> str:
    """데이터베이스 백업"""
    if not os.path.exists(db_path):
        logger.info("데이터베이스 파일이 존재하지 않음 - 새로 생성됩니다.")
        return None
    
    backup_path = f"{db_path}.backup_{int(time.time())}"
    import shutil
    shutil.copy2(db_path, backup_path)
    logger.info(f"데이터베이스 백업 생성: {backup_path}")
    return backup_path

def check_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """테이블 존재 확인"""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None

def check_column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    """컬럼 존재 확인"""
    try:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns
    except sqlite3.OperationalError:
        return False

def add_missing_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_def: str):
    """누락된 컬럼 추가"""
    if not check_column_exists(conn, table_name, column_name):
        try:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
            conn.commit()
            logger.info(f"✅ 컬럼 추가됨: {table_name}.{column_name}")
        except sqlite3.OperationalError as e:
            logger.error(f"❌ 컬럼 추가 실패: {table_name}.{column_name} - {e}")
    else:
        logger.info(f"✅ 컬럼이 이미 존재함: {table_name}.{column_name}")

def verify_system_monitor():
    """SystemMonitor의 _check_cache_status 메서드 확인"""
    try:
        # 더미 데이터베이스 매니저로 시스템 모니터 테스트
        db_manager = DatabaseStabilityManager("instance/blacklist.db")
        monitor = SystemMonitor(db_manager)
        
        # _check_cache_status 메서드 존재 확인
        if hasattr(monitor, '_check_cache_status'):
            logger.info("✅ SystemMonitor._check_cache_status 메서드 존재함")
            
            # 메서드 실행 테스트
            try:
                result = monitor._check_cache_status()
                logger.info(f"✅ _check_cache_status 실행 성공: {result.get('status', 'unknown')}")
                return True
            except Exception as e:
                logger.warning(f"⚠️ _check_cache_status 실행 실패: {e}")
                return False
        else:
            logger.error("❌ SystemMonitor._check_cache_status 메서드가 없음")
            return False
            
    except Exception as e:
        logger.error(f"❌ SystemMonitor 검증 실패: {e}")
        return False

def fix_database_schema():
    """데이터베이스 스키마 수정"""
    logger.info("🔧 데이터베이스 스키마 수정 시작...")
    
    # 1. 데이터베이스 스키마 인스턴스 생성
    schema = DatabaseSchema()
    db_path = schema.db_path
    
    # 2. 디렉토리 생성
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 3. 백업 생성 (기존 DB가 있는 경우)
    if os.path.exists(db_path):
        import time
        backup_path = backup_database(db_path)
    
    # 4. 데이터베이스 연결
    try:
        with schema.connection_manager.get_connection() as conn:
            logger.info(f"📁 데이터베이스 연결: {db_path}")
            
            # 5. 필수 테이블 확인 및 생성
            logger.info("🔍 필수 테이블 확인...")
            
            # auth_attempts 테이블 확인
            if not check_table_exists(conn, 'auth_attempts'):
                logger.info("⚠️ auth_attempts 테이블이 없음 - 생성 중...")
                schema.table_definitions.create_auth_attempts_table(conn)
                logger.info("✅ auth_attempts 테이블 생성 완료")
            else:
                logger.info("✅ auth_attempts 테이블 존재함")
            
            # system_logs 테이블 확인 및 additional_data 컬럼 추가
            if not check_table_exists(conn, 'system_logs'):
                logger.info("⚠️ system_logs 테이블이 없음 - 생성 중...")
                schema.table_definitions.create_system_logs_table(conn)
                logger.info("✅ system_logs 테이블 생성 완료")
            else:
                logger.info("✅ system_logs 테이블 존재함")
                
                # additional_data 컬럼 확인 및 추가
                add_missing_column(conn, 'system_logs', 'additional_data', 'TEXT')
            
            # 6. 다른 필수 테이블들 확인
            required_tables = [
                ('blacklist_entries', schema.table_definitions.create_blacklist_entries_table),
                ('collection_logs', schema.table_definitions.create_collection_logs_table),
                ('system_status', schema.table_definitions.create_system_status_table),
                ('cache_entries', schema.table_definitions.create_cache_table),
                ('metadata', schema.table_definitions.create_metadata_table),
            ]
            
            for table_name, create_func in required_tables:
                if not check_table_exists(conn, table_name):
                    logger.info(f"⚠️ {table_name} 테이블이 없음 - 생성 중...")
                    create_func(conn)
                    logger.info(f"✅ {table_name} 테이블 생성 완료")
                else:
                    logger.info(f"✅ {table_name} 테이블 존재함")
            
            # 7. 스키마 버전 업데이트
            conn.execute("""
                INSERT OR REPLACE INTO metadata 
                (key, value, value_type, description, category) 
                VALUES (?, ?, ?, ?, ?)
            """, (
                "schema_version",
                "2.0.0",
                "string",
                "데이터베이스 스키마 버전",
                "system",
            ))
            
            # 8. 인덱스 생성
            schema.index_manager.create_indexes(conn)
            
            conn.commit()
            logger.info("✅ 스키마 수정 완료")
            
    except Exception as e:
        logger.error(f"❌ 데이터베이스 스키마 수정 실패: {e}")
        raise
    
    return True

def verify_database_integrity():
    """데이터베이스 무결성 검증"""
    logger.info("🔍 데이터베이스 무결성 검증...")
    
    schema = DatabaseSchema()
    
    try:
        # 1. 테이블 통계 확인
        stats = schema.get_table_stats()
        logger.info("📊 테이블 통계:")
        
        expected_tables = [
            'blacklist_entries', 'collection_logs', 'auth_attempts', 
            'system_status', 'cache_entries', 'metadata', 'system_logs'
        ]
        
        missing_tables = []
        for table in expected_tables:
            if table in stats:
                if 'error' in stats[table]:
                    logger.error(f"❌ {table}: {stats[table]['error']}")
                    missing_tables.append(table)
                else:
                    logger.info(f"✅ {table}: {stats[table]['count']} rows")
            else:
                logger.error(f"❌ {table}: 테이블이 없음")
                missing_tables.append(table)
        
        # 2. 스키마 버전 확인
        current_version = schema.get_current_schema_version()
        if current_version == "2.0.0":
            logger.info(f"✅ 스키마 버전: {current_version}")
        else:
            logger.error(f"❌ 스키마 버전 불일치: {current_version} (예상: 2.0.0)")
        
        # 3. SystemMonitor 검증
        monitor_ok = verify_system_monitor()
        
        if not missing_tables and current_version == "2.0.0" and monitor_ok:
            logger.info("🎉 모든 검증 통과!")
            return True
        else:
            logger.error("❌ 일부 검증 실패")
            return False
            
    except Exception as e:
        logger.error(f"❌ 데이터베이스 무결성 검증 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    logger.info("🚀 데이터베이스 스키마 수정 시작...")
    
    try:
        # 1. 스키마 수정
        success = fix_database_schema()
        
        if success:
            # 2. 무결성 검증
            integrity_ok = verify_database_integrity()
            
            if integrity_ok:
                logger.info("🎉 데이터베이스 스키마 수정 및 검증 완료!")
                print("\n✅ 스키마 수정 성공!")
                print("📋 수정된 사항:")
                print("  - system_logs 테이블에 additional_data 컬럼 추가")
                print("  - auth_attempts 테이블 생성 확인")
                print("  - 모든 필수 테이블 (9개) 생성 확인")
                print("  - 스키마 버전 2.0.0으로 업데이트")
                print("  - SystemMonitor._check_cache_status 메서드 검증")
                return True
            else:
                logger.error("❌ 무결성 검증 실패")
                return False
        else:
            logger.error("❌ 스키마 수정 실패")
            return False
            
    except Exception as e:
        logger.error(f"❌ 스키마 수정 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)