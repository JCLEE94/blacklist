"""
데이터베이스 연결 관리

SQLite 데이터베이스 연결을 최적화하고 관리합니다.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ConnectionManager:
    """데이터베이스 연결 관리 클래스"""
    
    def __init__(self, db_path: str = "instance/blacklist.db"):
        self.db_path = db_path
        self._memory_connection = None  # Persistent connection for in-memory DBs
        
        # Handle DATABASE_URL environment variable
        import os
        if os.getenv('DATABASE_URL'):
            database_url = os.getenv('DATABASE_URL')
            if database_url.startswith("sqlite:///"):
                self.db_path = database_url.replace("sqlite:///", "")
            elif database_url == "sqlite:///:memory:":
                self.db_path = ":memory:"
    
    def get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 반환"""
        
        # For in-memory databases, use persistent connection to avoid losing data
        if self.db_path == ":memory:":
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(self.db_path)
                self._memory_connection.row_factory = sqlite3.Row
                self._configure_memory_connection(self._memory_connection)
            return self._memory_connection
        
        # For file-based databases, create new connections as before
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        self._configure_file_connection(conn)
        return conn
    
    def _configure_memory_connection(self, conn: sqlite3.Connection):
        """인메모리 데이터베이스 연결 설정"""
        conn.execute("PRAGMA synchronous=OFF")  # Fast for memory
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
    
    def _configure_file_connection(self, conn: sqlite3.Connection):
        """파일 데이터베이스 연결 설정"""
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
    
    def close_memory_connection(self):
        """인메모리 연결 닫기"""
        if self._memory_connection:
            self._memory_connection.close()
            self._memory_connection = None
