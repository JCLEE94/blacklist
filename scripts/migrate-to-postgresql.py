#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
Migrates existing SQLite data to PostgreSQL database
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import logging
from datetime import datetime
from typing import List, Dict, Any
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self):
        self.sqlite_path = '/home/jclee/app/blacklist/instance/blacklist.db'
        self.pg_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'blacklist',
            'user': 'blacklist_user',
            'password': 'blacklist_password_change_me'
        }
        
    def connect_sqlite(self):
        """SQLite 연결"""
        if not os.path.exists(self.sqlite_path):
            logger.warning(f"SQLite database not found: {self.sqlite_path}")
            return None
        return sqlite3.connect(self.sqlite_path)
    
    def connect_postgresql(self):
        """PostgreSQL 연결"""
        try:
            return psycopg2.connect(**self.pg_config)
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return None
    
    def get_table_data(self, sqlite_conn, table_name: str) -> List[Dict]:
        """SQLite 테이블에서 데이터 추출"""
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
        except sqlite3.Error as e:
            logger.warning(f"Failed to read table {table_name}: {e}")
            return []
    
    def convert_data_types(self, data: List[Dict], table_name: str) -> List[Dict]:
        """데이터 타입 변환 (SQLite -> PostgreSQL)"""
        converted_data = []
        
        for row in data:
            converted_row = {}
            for key, value in row.items():
                # IP 주소 필드 처리
                if 'ip_address' in key and value:
                    converted_row[key] = str(value)
                # JSON 필드 처리
                elif key in ['details', 'config'] and value:
                    try:
                        if isinstance(value, str):
                            json.loads(value)  # 유효성 검사
                            converted_row[key] = value
                        else:
                            converted_row[key] = json.dumps(value)
                    except:
                        converted_row[key] = json.dumps(str(value))
                # 날짜 필드 처리
                elif 'date' in key or 'timestamp' in key or key.endswith('_at'):
                    if value:
                        try:
                            # SQLite 날짜/시간 문자열을 그대로 사용
                            converted_row[key] = value
                        except:
                            converted_row[key] = None
                    else:
                        converted_row[key] = None
                else:
                    converted_row[key] = value
            
            converted_data.append(converted_row)
        
        return converted_data
    
    def insert_data(self, pg_conn, table_name: str, data: List[Dict]):
        """PostgreSQL에 데이터 삽입"""
        if not data:
            logger.info(f"No data to migrate for table: {table_name}")
            return
        
        try:
            cursor = pg_conn.cursor()
            
            # 컬럼명과 값 준비
            columns = list(data[0].keys())
            values = [[row[col] for col in columns] for row in data]
            
            # INSERT 쿼리 생성
            placeholders = ','.join(['%s'] * len(columns))
            query = f"""
                INSERT INTO {table_name} ({','.join(columns)})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            
            # 배치 삽입
            execute_values(cursor, query, values, page_size=1000)
            pg_conn.commit()
            
            logger.info(f"Migrated {len(data)} rows to {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to insert data into {table_name}: {e}")
            pg_conn.rollback()
    
    def migrate_table(self, sqlite_conn, pg_conn, table_name: str):
        """단일 테이블 마이그레이션"""
        logger.info(f"Migrating table: {table_name}")
        
        # SQLite에서 데이터 추출
        data = self.get_table_data(sqlite_conn, table_name)
        if not data:
            return
        
        # 데이터 타입 변환
        converted_data = self.convert_data_types(data, table_name)
        
        # PostgreSQL에 삽입
        self.insert_data(pg_conn, table_name, converted_data)
    
    def run_migration(self):
        """전체 마이그레이션 실행"""
        logger.info("🚀 Starting SQLite to PostgreSQL migration...")
        
        # 연결 설정
        sqlite_conn = self.connect_sqlite()
        pg_conn = self.connect_postgresql()
        
        if not sqlite_conn:
            logger.error("Cannot proceed without SQLite connection")
            return False
        
        if not pg_conn:
            logger.error("Cannot proceed without PostgreSQL connection")
            return False
        
        try:
            # 마이그레이션할 테이블 목록
            tables_to_migrate = [
                'blacklist',
                'blacklist_entries', 
                'metadata',
                'collection_logs',
                'auth_attempts',
                'system_status',
                'cache_entries',
                'system_logs',
                'collection_sources',
                'collection_credentials',
                'collection_settings',
                'collection_history'
            ]
            
            # 각 테이블 마이그레이션
            for table in tables_to_migrate:
                self.migrate_table(sqlite_conn, pg_conn, table)
            
            # 시퀀스 재설정
            self.reset_sequences(pg_conn)
            
            logger.info("✅ Migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
        finally:
            sqlite_conn.close()
            pg_conn.close()
    
    def reset_sequences(self, pg_conn):
        """시퀀스 재설정"""
        try:
            cursor = pg_conn.cursor()
            
            # 각 테이블의 시퀀스 재설정
            sequence_queries = [
                "SELECT setval('blacklist_id_seq', COALESCE((SELECT MAX(id) FROM blacklist), 1));",
                "SELECT setval('collection_logs_id_seq', COALESCE((SELECT MAX(id) FROM collection_logs), 1));",
                "SELECT setval('auth_attempts_id_seq', COALESCE((SELECT MAX(id) FROM auth_attempts), 1));",
                "SELECT setval('system_status_id_seq', COALESCE((SELECT MAX(id) FROM system_status), 1));",
                "SELECT setval('system_logs_id_seq', COALESCE((SELECT MAX(id) FROM system_logs), 1));",
                "SELECT setval('collection_sources_id_seq', COALESCE((SELECT MAX(id) FROM collection_sources), 1));",
                "SELECT setval('collection_credentials_id_seq', COALESCE((SELECT MAX(id) FROM collection_credentials), 1));",
                "SELECT setval('collection_settings_id_seq', COALESCE((SELECT MAX(id) FROM collection_settings), 1));",
                "SELECT setval('collection_history_id_seq', COALESCE((SELECT MAX(id) FROM collection_history), 1));"
            ]
            
            for query in sequence_queries:
                try:
                    cursor.execute(query)
                except Exception as e:
                    logger.warning(f"Failed to reset sequence: {e}")
            
            pg_conn.commit()
            logger.info("Sequences reset successfully")
            
        except Exception as e:
            logger.error(f"Failed to reset sequences: {e}")

if __name__ == "__main__":
    migrator = DatabaseMigrator()
    success = migrator.run_migration()
    
    if success:
        print("🎉 Migration completed successfully!")
        print("You can now update your application to use PostgreSQL")
    else:
        print("❌ Migration failed - check logs for details")
        exit(1)