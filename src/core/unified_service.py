#!/usr/bin/env python3
"""
통합 블랙리스트 관리 서비스
모든 블랙리스트 운영을 하나로 통합한 서비스
"""
import os
import logging
import asyncio
import json
import sqlite3
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .container import get_container
from .regtech_collector import RegtechCollector
from .secudium_collector import SecudiumCollector
from .blacklist_unified import UnifiedBlacklistManager
from .collection_manager import CollectionManager

logger = logging.getLogger(__name__)

@dataclass
class ServiceHealth:
    status: str
    components: Dict[str, str]
    timestamp: datetime
    version: str

class UnifiedBlacklistService:
    """
    통합 블랙리스트 서비스 - 모든 기능을 하나로 통합
    REGTECH, SECUDIUM 수집부터 API 서빙까지 단일 서비스로 처리
    """
    
    def __init__(self):
        self.container = get_container()
        self.logger = logging.getLogger(__name__)
        
        # 서비스 상태
        self._running = False
        self._components = {}
        
        # 통합 설정
        self.config = {
            'regtech_enabled': os.getenv('REGTECH_ENABLED', 'true').lower() == 'true',
            'secudium_enabled': os.getenv('SECUDIUM_ENABLED', 'true').lower() == 'true',
            'auto_collection': os.getenv('AUTO_COLLECTION', 'true').lower() == 'true',
            'collection_interval': int(os.getenv('COLLECTION_INTERVAL', 3600)),
            'service_name': 'blacklist-unified',
            'version': '3.0.0'
        }
        
        # 수집 로그 저장 (메모리, 최대 1000개)
        self.collection_logs = []
        self.max_logs = 1000
        
        # Initialize core services immediately
        try:
            self.blacklist_manager = self.container.resolve('blacklist_manager')
            self.cache = self.container.resolve('cache_manager')
            # Try to get collection_manager
            try:
                self.collection_manager = self.container.resolve('collection_manager')
            except Exception as e:
                self.logger.warning(f"Collection Manager not available: {e}")
                self.collection_manager = None
        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            self.blacklist_manager = None
            self.cache = None
            self.collection_manager = None
        
        # 로그 테이블 초기화
        self._ensure_log_table()
        
        # 데이터베이스에서 기존 로그 로드
        try:
            existing_logs = self._load_logs_from_db(100)
            self.collection_logs = existing_logs
        except Exception as e:
            self.logger.warning(f"Failed to load existing logs: {e}")
        
        # Mark as running for basic health checks
        self._running = True
        
    async def start(self) -> None:
        """통합 서비스 시작"""
        self.logger.info("🚀 통합 블랙리스트 서비스 시작...")
        
        try:
            # 1. 의존성 컨테이너 초기화
            await self._initialize_container()
            
            # 2. 핵심 컴포넌트 초기화
            await self._initialize_components()
            
            # 3. 백그라운드 작업 시작
            if self.config['auto_collection']:
                await self._start_background_tasks()
            
            self._running = True
            self.logger.info("✅ 통합 블랙리스트 서비스 시작 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 서비스 시작 실패: {e}")
            raise
    
    async def stop(self) -> None:
        """통합 서비스 정지"""
        self.logger.info("🛑 통합 블랙리스트 서비스 정지...")
        
        # 백그라운드 작업 정지
        if hasattr(self, '_background_tasks'):
            for task in self._background_tasks:
                task.cancel()
        
        # 컴포넌트 정리
        await self._cleanup_components()
        
        self._running = False
        self.logger.info("✅ 통합 블랙리스트 서비스 정지 완료")
    
    async def _initialize_container(self):
        """의존성 컨테이너 초기화"""
        self.logger.info("📦 의존성 컨테이너 초기화 중...")
        
        # Already initialized in __init__, just verify they exist
        if not self.blacklist_manager:
            self.logger.error("blacklist_manager not initialized")
            raise RuntimeError("Required service 'blacklist_manager' not available")
        
        if not self.cache:
            self.logger.error("cache not initialized")
            raise RuntimeError("Required service 'cache' not available")
        
        self.logger.info("✅ 의존성 컨테이너 초기화 완료")
    
    async def _initialize_components(self):
        """핵심 컴포넌트 초기화"""
        self.logger.info("⚙️ 핵심 컴포넌트 초기화 중...")
        
        # REGTECH 수집기 초기화
        if self.config['regtech_enabled']:
            self._components['regtech'] = RegtechCollector('data', self.cache)
            self.logger.info("✅ REGTECH 수집기 초기화 완료")
        
        # SECUDIUM 수집기 초기화
        if self.config['secudium_enabled']:
            self._components['secudium'] = SecudiumCollector('data', self.cache)
            self.logger.info("✅ SECUDIUM 수집기 초기화 완료")
        
        self.logger.info("✅ 모든 컴포넌트 초기화 완료")
    
    async def _start_background_tasks(self):
        """백그라운드 자동 수집 작업 시작"""
        self.logger.info("🔄 자동 수집 작업 시작...")
        
        self._background_tasks = []
        
        # 주기적 수집 작업
        collection_task = asyncio.create_task(self._periodic_collection())
        self._background_tasks.append(collection_task)
        
        self.logger.info("✅ 백그라운드 작업 시작 완료")
    
    async def _periodic_collection(self):
        """주기적 데이터 수집"""
        while self._running:
            try:
                # 일일 자동 수집이 활성화된 경우만 실행
                if self.collection_manager and hasattr(self.collection_manager, 'daily_collection_enabled'):
                    if self.collection_manager.daily_collection_enabled:
                        # 마지막 수집이 오늘이 아니면 수집 실행
                        last_collection = self.collection_manager.last_daily_collection
                        if not last_collection or not last_collection.startswith(datetime.now().strftime('%Y-%m-%d')):
                            self.logger.info("🔄 일일 자동 수집 시작...")
                            
                            # 오늘 날짜로 수집
                            today = datetime.now()
                            start_date = today.strftime('%Y%m%d')
                            end_date = today.strftime('%Y%m%d')
                            
                            # REGTECH 수집 (하루 단위)
                            result = await self._collect_regtech_data_with_date(start_date, end_date)
                            
                            if result.get('success'):
                                self.logger.info(f"✅ 일일 자동 수집 완료: {result.get('total_collected', 0)}개 IP")
                                
                                # 마지막 수집 시간 업데이트
                                self.collection_manager.last_daily_collection = datetime.now().isoformat()
                                self.collection_manager.config['last_daily_collection'] = self.collection_manager.last_daily_collection
                                self.collection_manager._save_collection_config()
                            else:
                                self.logger.warning("⚠️ 일일 자동 수집 실패")
                
                # 다음 체크까지 대기 (1시간)
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"❌ 주기적 수집 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 후 재시도
    
    async def _cleanup_components(self):
        """컴포넌트 정리"""
        self.logger.info("🧹 컴포넌트 정리 중...")
        
        for name, component in self._components.items():
            try:
                if hasattr(component, 'cleanup'):
                    await component.cleanup()
            except Exception as e:
                self.logger.warning(f"컴포넌트 {name} 정리 중 오류: {e}")
    
    # === 통합 API 메서드들 ===
    
    async def collect_all_data(self, force: bool = False) -> Dict[str, Any]:
        """모든 소스에서 데이터 수집"""
        self.logger.info("🔄 전체 데이터 수집 시작...")
        
        results = {}
        total_success = 0
        total_failed = 0
        
        # REGTECH 수집
        if 'regtech' in self._components:
            try:
                regtech_result = await self._collect_regtech_data(force)
                results['regtech'] = regtech_result
                if regtech_result.get('success'):
                    total_success += 1
                else:
                    total_failed += 1
            except Exception as e:
                self.logger.error(f"REGTECH 수집 실패: {e}")
                results['regtech'] = {'success': False, 'error': str(e)}
                total_failed += 1
        
        # SECUDIUM 수집
        if 'secudium' in self._components:
            try:
                secudium_result = await self._collect_secudium_data(force)
                results['secudium'] = secudium_result
                if secudium_result.get('success'):
                    total_success += 1
                else:
                    total_failed += 1
            except Exception as e:
                self.logger.error(f"SECUDIUM 수집 실패: {e}")
                results['secudium'] = {'success': False, 'error': str(e)}
                total_failed += 1
        
        return {
            'success': total_success > 0,
            'results': results,
            'summary': {
                'successful_sources': total_success,
                'failed_sources': total_failed,
                'timestamp': datetime.now().isoformat()
            }
        }
    
    async def _collect_regtech_data(self, force: bool = False) -> Dict[str, Any]:
        """REGTECH 데이터 수집"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._components['regtech'].auto_collect
        )
    
    async def _collect_regtech_data_with_date(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """REGTECH 데이터 수집 (날짜 지정)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._components['regtech'].collect_from_web,
            5,  # max_pages
            100,  # page_size
            1,  # parallel_workers
            start_date,
            end_date
        )
    
    async def _collect_secudium_data(self, force: bool = False) -> Dict[str, Any]:
        """SECUDIUM 데이터 수집"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._components['secudium'].auto_collect
        )
    
    async def search_ip(self, ip: str) -> Dict[str, Any]:
        """통합 IP 검색"""
        try:
            # 블랙리스트 매니저를 통한 통합 검색
            result = self.blacklist_manager.search_ip(ip)
            return {
                'success': True,
                'ip': ip,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"IP 검색 실패 ({ip}): {e}")
            return {
                'success': False,
                'ip': ip,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_active_blacklist(self, format_type: str = 'json') -> Dict[str, Any]:
        """활성 블랙리스트 조회"""
        try:
            # Check if blacklist_manager is available
            if not self.blacklist_manager:
                return {
                    'success': False,
                    'error': "Blacklist manager not initialized",
                    'timestamp': datetime.now().isoformat()
                }
            
            if format_type == 'fortigate':
                # FortiGate 형식으로 변환
                active_ips = self.blacklist_manager.get_active_ips()
                result = {
                    "version": "1.0",
                    "name": "Blacklist IPs",
                    "category": "Secudium Blacklist",
                    "description": "Threat Intelligence Blacklist",
                    "entries": [{"ip": ip} for ip in sorted(active_ips)],
                    "total_count": len(active_ips),
                    "generated_at": datetime.now().isoformat()
                }
            else:
                active_ips = self.blacklist_manager.get_active_ips()
                result = {
                    "ips": list(active_ips),
                    "count": len(active_ips),
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                'success': True,
                'format': format_type,
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"블랙리스트 조회 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """통합 시스템 통계"""
        try:
            # Check if blacklist_manager is available
            if not self.blacklist_manager:
                return {
                    'success': False,
                    'error': "Blacklist manager not initialized",
                    'timestamp': datetime.now().isoformat()
                }
            
            # Get system health which includes stats
            health_data = self.blacklist_manager.get_system_health()
            
            # Extract stats from health data
            stats = {
                'total_ips': len(self.blacklist_manager.get_active_ips()),
                'sources': health_data.get('sources', {}),
                'status': health_data.get('status', 'unknown'),
                'last_update': health_data.get('last_update', None)
            }
            
            # 서비스 상태 추가
            stats['service'] = {
                'name': self.config['service_name'],
                'version': self.config['version'],
                'running': self._running,
                'components': list(self._components.keys()),
                'auto_collection': self.config['auto_collection'],
                'collection_interval': self.config['collection_interval']
            }
            
            return {
                'success': True,
                'statistics': stats,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"통계 조회 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_health(self) -> ServiceHealth:
        """서비스 헬스 체크"""
        component_status = {}
        
        for name, component in self._components.items():
            try:
                # 각 컴포넌트의 상태 확인
                if hasattr(component, 'get_health'):
                    component_status[name] = component.get_health()
                else:
                    component_status[name] = "healthy"
            except Exception as e:
                component_status[name] = f"error: {e}"
        
        # 전체 상태 결정
        overall_status = "healthy" if self._running else "stopped"
        if any("error" in status for status in component_status.values()):
            overall_status = "degraded"
        
        return ServiceHealth(
            status=overall_status,
            components=component_status,
            timestamp=datetime.now(),
            version=self.config['version']
        )
    
    
    def initialize_database_tables(self) -> Dict[str, Any]:
        """데이터베이스 테이블 강제 초기화"""
        try:
            # Use blacklist_manager's database path
            if hasattr(self.blacklist_manager, 'db_path'):
                db_path = self.blacklist_manager.db_path
            else:
                db_path = os.path.join('/app' if os.path.exists('/app') else '.', 'instance/blacklist.db')
            
            self.logger.info(f"Initializing database tables at: {db_path}")
            
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create blacklist_ip table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blacklist_ip (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    detection_date TEXT,
                    attack_type TEXT,
                    country TEXT,
                    source TEXT,
                    confidence_score REAL DEFAULT 1.0,
                    is_active INTEGER DEFAULT 1,
                    last_seen TEXT
                )
            """)
            
            # Create ip_detection table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_detection (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    attack_type TEXT,
                    confidence_score REAL DEFAULT 1.0,
                    FOREIGN KEY (ip) REFERENCES blacklist_ip(ip)
                )
            """)
            
            # Create collection_logs table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_ip_source ON blacklist_ip(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_ip_created_at ON blacklist_ip(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_collection_logs_created_at ON collection_logs(created_at DESC)")
            
            conn.commit()
            conn.close()
            
            self.logger.info("Database tables initialized successfully")
            return {
                'success': True,
                'message': 'Database tables initialized',
                'database_path': db_path
            }
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database tables: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_source_counts_from_db(self) -> Dict[str, int]:
        """데이터베이스에서 소스별 IP 개수 조회"""
        source_counts = {'REGTECH': 0, 'SECUDIUM': 0, 'PUBLIC': 0}
        try:
            # Use blacklist_manager's database path
            if hasattr(self.blacklist_manager, 'db_path'):
                db_path = self.blacklist_manager.db_path
            else:
                # Fallback to instance path
                db_path = os.path.join('/app' if os.path.exists('/app') else '.', 'instance/blacklist.db')
            
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT source, COUNT(*) FROM blacklist_ip GROUP BY source")
            for row in cursor.fetchall():
                if row[0] in source_counts:
                    source_counts[row[0]] = row[1]
            conn.close()
        except Exception as e:
            self.logger.warning(f"Failed to get source counts from database: {e}")
        return source_counts
    
    def get_collection_status(self) -> Dict[str, Any]:
        """수집 시스템 상태 조회"""
        try:
            if self.collection_manager:
                # Get status from collection manager
                cm_status = self.collection_manager.get_status()
                
                # Return properly formatted response
                return {
                    'enabled': cm_status.get('collection_enabled', False),
                    'status': cm_status.get('status', 'inactive'),
                    'sources': cm_status.get('sources', {}),
                    'stats': {
                        'total_ips': cm_status.get('summary', {}).get('total_ips_collected', 0),
                        'today_collected': 0  # Placeholder
                    },
                    'last_collection': cm_status.get('last_updated'),
                    'last_enabled_at': cm_status.get('last_enabled_at'),
                    'last_disabled_at': cm_status.get('last_disabled_at')
                }
            else:
                # Fallback when collection_manager is not available
                # Get actual counts from database
                source_counts = self._get_source_counts_from_db()
                total_ips = sum(source_counts.values())
                
                return {
                    'enabled': True,
                    'status': 'active',
                    'sources': {
                        'regtech': {
                            'enabled': self.config.get('regtech_enabled', True),
                            'status': 'has_data' if source_counts.get('REGTECH', 0) > 0 else 'no_data',
                            'total_ips': source_counts.get('REGTECH', 0),
                            'name': 'REGTECH (금융보안원)',
                            'manual_only': True,
                            'last_collection': None
                        },
                        'secudium': {
                            'enabled': self.config.get('secudium_enabled', True),
                            'status': 'has_data' if source_counts.get('SECUDIUM', 0) > 0 else 'no_data',
                            'total_ips': source_counts.get('SECUDIUM', 0),
                            'name': 'SECUDIUM (에스케이인포섹)',
                            'manual_only': True,
                            'last_collection': None
                        }
                    },
                    'stats': {
                        'total_ips': total_ips,
                        'today_collected': 0
                    },
                    'last_collection': datetime.now().isoformat()
                }
        except Exception as e:
            self.logger.error(f"수집 상태 조회 실패: {e}")
            return {
                'enabled': False,
                'status': 'error',
                'error': str(e),
                'sources': {}
            }
    
    def get_system_health(self) -> Dict[str, Any]:
        """시스템 헬스 정보 반환 (unified_routes에서 사용)"""
        try:
            # Check if blacklist_manager is available
            if not self.blacklist_manager:
                return {
                    'status': 'unhealthy',
                    'total_ips': 0,
                    'active_ips': 0,
                    'error': 'Blacklist manager not initialized'
                }
            
            # Get active IPs
            active_ips = self.blacklist_manager.get_active_ips()
            if isinstance(active_ips, tuple):
                active_ips = active_ips[0]  # Get the actual list from tuple
            
            total_ips = len(active_ips) if active_ips else 0
            
            # Get actual counts by source from database
            source_counts = {'REGTECH': 0, 'SECUDIUM': 0, 'PUBLIC': 0}
            try:
                # Use blacklist_manager's database path
                if hasattr(self.blacklist_manager, 'db_path'):
                    db_path = self.blacklist_manager.db_path
                else:
                    # Fallback to instance path
                    db_path = os.path.join('/app' if os.path.exists('/app') else '.', 'instance/blacklist.db')
                
                self.logger.info(f"Getting source counts from database: {db_path}")
                self.logger.info(f"Database file exists: {os.path.exists(db_path)}")
                if os.path.exists(db_path):
                    self.logger.info(f"Database file size: {os.path.getsize(db_path)} bytes")
                
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='blacklist_ip'")
                table_exists = cursor.fetchone()
                self.logger.info(f"blacklist_ip table exists: {table_exists is not None}")
                
                if not table_exists:
                    self.logger.warning("blacklist_ip table does not exist! Creating tables...")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS blacklist_ip (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ip TEXT NOT NULL UNIQUE,
                            created_at TEXT NOT NULL,
                            detection_date TEXT,
                            attack_type TEXT,
                            country TEXT,
                            source TEXT,
                            confidence_score REAL DEFAULT 1.0,
                            is_active INTEGER DEFAULT 1,
                            last_seen TEXT
                        )
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS ip_detection (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ip TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            source TEXT NOT NULL,
                            attack_type TEXT,
                            confidence_score REAL DEFAULT 1.0
                        )
                    """)
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_ip_source ON blacklist_ip(source)")
                    conn.commit()
                    self.logger.info("Database tables created successfully!")
                
                if table_exists or True:  # Always check after potential creation
                    # First check if table exists and has data
                    cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
                    total_in_db = cursor.fetchone()[0]
                    self.logger.info(f"Total IPs in database: {total_in_db}")
                    
                    # 더 상세한 디버깅 정보
                    if total_in_db > 0:
                        cursor.execute("SELECT source, COUNT(*) FROM blacklist_ip GROUP BY source")
                        for row in cursor.fetchall():
                            self.logger.info(f"Source {row[0]}: {row[1]} IPs")
                            if row[0] in source_counts:
                                source_counts[row[0]] = row[1]
                        
                        # 최근 추가된 데이터 확인
                        cursor.execute("SELECT ip, source, created_at FROM blacklist_ip ORDER BY created_at DESC LIMIT 5")
                        recent_ips = cursor.fetchall()
                        self.logger.info(f"Recent IPs added: {recent_ips}")
                    else:
                        self.logger.warning("No IPs found in database - checking table structure...")
                        cursor.execute("PRAGMA table_info(blacklist_ip)")
                        table_info = cursor.fetchall()
                        self.logger.info(f"Table structure: {table_info}")
                        
                        # 모든 테이블 확인
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        all_tables = cursor.fetchall()
                        self.logger.info(f"All tables in database: {all_tables}")
                    
                    total_ips = total_in_db  # Use the actual count from database
                conn.close()
            except Exception as e:
                self.logger.warning(f"Failed to get source counts: {e}")
                import traceback
                self.logger.warning(f"Traceback: {traceback.format_exc()}")
            
            return {
                'status': 'healthy' if self._running else 'stopped',
                'total_ips': total_ips,
                'active_ips': total_ips,
                'regtech_count': source_counts.get('REGTECH', 0),
                'secudium_count': source_counts.get('SECUDIUM', 0),
                'public_count': source_counts.get('PUBLIC', 0),
                'sources': {
                    'regtech': {'enabled': self.config.get('regtech_enabled', False), 'count': source_counts.get('REGTECH', 0)},
                    'secudium': {'enabled': self.config.get('secudium_enabled', False), 'count': source_counts.get('SECUDIUM', 0)}
                },
                'last_update': datetime.now().isoformat(),
                'cache_available': self.cache is not None,
                'database_connected': True,
                'version': self.config.get('version', '3.0.0')
            }
        except Exception as e:
            self.logger.error(f"Failed to get system health: {e}")
            return {
                'status': 'error',
                'total_ips': 0,
                'active_ips': 0,
                'error': str(e)
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """시스템 통계 반환"""
        return self.get_system_health()  # Reuse system health data
    
    def add_collection_log(self, source: str, action: str, details: Dict[str, Any] = None):
        """수집 로그 추가 - 메모리와 데이터베이스에 저장"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'action': action,
            'details': details or {}
        }
        
        # 메모리에 로그 추가
        self.collection_logs.append(log_entry)
        
        # 최대 개수 유지
        if len(self.collection_logs) > self.max_logs:
            self.collection_logs = self.collection_logs[-self.max_logs:]
            
        # 데이터베이스에도 저장
        try:
            self._save_log_to_db(log_entry)
        except Exception as e:
            self.logger.warning(f"Failed to save log to database: {e}")
            
        # 콘솔에도 출력 (일일 통계 포함)
        if action in ['collection_complete', 'collection_start']:
            ip_count = details.get('ip_count', 0) if details else 0
            self.logger.info(f"📊 {source} {action}: {ip_count}개 IP 처리")
        else:
            self.logger.info(f"📝 {source}: {action}")
    
    def get_collection_logs(self, limit: int = 100) -> list:
        """최근 수집 로그 반환 - 데이터베이스와 메모리에서 통합"""
        try:
            # 데이터베이스에서 최근 로그 조회
            db_logs = self._load_logs_from_db(limit)
            
            # 메모리의 최신 로그와 병합
            all_logs = db_logs + self.collection_logs[-50:]  # 메모리에서 최신 50개
            
            # 중복 제거 및 시간순 정렬
            unique_logs = {}
            for log in all_logs:
                key = f"{log['timestamp']}_{log['source']}_{log['action']}"
                unique_logs[key] = log
                
            sorted_logs = sorted(unique_logs.values(), 
                               key=lambda x: x['timestamp'], reverse=True)
            
            return sorted_logs[:limit]
        except Exception as e:
            self.logger.warning(f"Failed to load logs from database: {e}")
            # 데이터베이스 실패 시 메모리 로그만 반환
            return self.collection_logs[-limit:]

    def _save_log_to_db(self, log_entry: Dict[str, Any]):
        """로그를 데이터베이스에 저장"""
        try:
            # 데이터베이스 경로 결정
            db_path = None
            if self.blacklist_manager and hasattr(self.blacklist_manager, 'db_path'):
                db_path = self.blacklist_manager.db_path
            else:
                # Fallback to default path
                import os
                if os.path.exists('/app'):
                    db_path = '/app/instance/blacklist.db'
                else:
                    db_path = 'instance/blacklist.db'
            
            # JSON으로 details 직렬화
            details_json = json.dumps(log_entry['details']) if log_entry['details'] else '{}'
            
            query = """
            INSERT INTO collection_logs (timestamp, source, action, details, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """
            
            with sqlite3.connect(db_path) as conn:
                conn.execute(query, (
                    log_entry['timestamp'],
                    log_entry['source'],
                    log_entry['action'],
                    details_json
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.warning(f"Failed to save log to database: {e}")
            
    def _load_logs_from_db(self, limit: int = 100) -> list:
        """데이터베이스에서 로그 불러오기"""
        try:
            # 데이터베이스 경로 결정
            db_path = None
            if self.blacklist_manager and hasattr(self.blacklist_manager, 'db_path'):
                db_path = self.blacklist_manager.db_path
            else:
                # Fallback to default path
                import os
                if os.path.exists('/app'):
                    db_path = '/app/instance/blacklist.db'
                else:
                    db_path = 'instance/blacklist.db'
                    
            query = """
            SELECT timestamp, source, action, details
            FROM collection_logs
            ORDER BY created_at DESC
            LIMIT ?
            """
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(query, (limit,))
                rows = cursor.fetchall()
                
                logs = []
                for row in rows:
                    try:
                        details = json.loads(row[3]) if row[3] else {}
                    except (json.JSONDecodeError, TypeError):
                        details = {}
                        
                    logs.append({
                        'timestamp': row[0],
                        'source': row[1],
                        'action': row[2],
                        'details': details
                    })
                    
                return logs
                
        except Exception as e:
            self.logger.warning(f"Failed to load logs from database: {e}")
            return []
            
    def _ensure_log_table(self):
        """로그 테이블이 존재하는지 확인하고 생성"""
        try:
            # 데이터베이스 경로 결정
            db_path = None
            if self.blacklist_manager and hasattr(self.blacklist_manager, 'db_path'):
                db_path = self.blacklist_manager.db_path
            else:
                # Fallback to default path
                import os
                if os.path.exists('/app'):
                    db_path = '/app/instance/blacklist.db'
                else:
                    db_path = 'instance/blacklist.db'
            
            query = """
            CREATE TABLE IF NOT EXISTS collection_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            
            with sqlite3.connect(db_path) as conn:
                conn.execute(query)
                conn.commit()
                
                # 인덱스 생성
                conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_collection_logs_created_at 
                ON collection_logs(created_at DESC)
                """)
                conn.commit()
                
            self.logger.info(f"Collection logs table ensured at: {db_path}")
                
        except Exception as e:
            self.logger.warning(f"Failed to create log table: {e}")
    
    def clear_collection_logs(self):
        """수집 로그 초기화"""
        self.collection_logs = []
        self.logger.info("수집 로그가 초기화되었습니다")
    
    def get_active_blacklist_ips(self) -> list:
        """활성 블랙리스트 IP 목록 반환"""
        try:
            if not self.blacklist_manager:
                return []
            
            active_ips = self.blacklist_manager.get_active_ips()
            if isinstance(active_ips, tuple):
                active_ips = active_ips[0]  # Get the actual list from tuple
            
            return list(active_ips) if active_ips else []
        except Exception as e:
            self.logger.error(f"Failed to get active blacklist IPs: {e}")
            return []
    
    def format_for_fortigate(self, ips: list) -> Dict[str, Any]:
        """FortiGate 형식으로 변환"""
        return {
            "threat_feed": {
                "name": "Nextrade Blacklist",
                "description": "통합 위협 IP 목록",
                "entries": [{"ip": ip, "type": "malicious"} for ip in ips]
            },
            "total_count": len(ips),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_blacklist_paginated(self, page: int = 1, per_page: int = 100, source_filter: str = None) -> Dict[str, Any]:
        """페이징된 블랙리스트 반환"""
        try:
            ips = self.get_active_blacklist_ips()
            
            # Simple pagination
            start = (page - 1) * per_page
            end = start + per_page
            paginated_ips = ips[start:end]
            
            return {
                'page': page,
                'per_page': per_page,
                'total': len(ips),
                'pages': (len(ips) + per_page - 1) // per_page,
                'data': paginated_ips
            }
        except Exception as e:
            self.logger.error(f"Failed to get paginated blacklist: {e}")
            return {
                'page': page,
                'per_page': per_page,
                'total': 0,
                'pages': 0,
                'data': []
            }
    
    def search_ip(self, ip: str) -> Dict[str, Any]:
        """단일 IP 검색"""
        try:
            if not self.blacklist_manager:
                return {'found': False, 'ip': ip, 'error': 'Blacklist manager not initialized'}
            
            active_ips = self.get_active_blacklist_ips()
            found = ip in active_ips
            
            return {
                'found': found,
                'ip': ip,
                'status': 'active' if found else 'not_found',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to search IP {ip}: {e}")
            return {'found': False, 'ip': ip, 'error': str(e)}
    
    def search_batch_ips(self, ips: list) -> Dict[str, Any]:
        """배치 IP 검색"""
        results = {}
        for ip in ips:
            results[ip] = self.search_ip(ip)
        return results
    
    def get_analytics_summary(self, days: int = 7) -> Dict[str, Any]:
        """분석 요약 반환"""
        return {
            'period_days': days,
            'total_ips': len(self.get_active_blacklist_ips()),
            'new_ips_today': 0,  # Placeholder
            'removed_ips_today': 0,  # Placeholder
            'top_sources': [
                {'name': 'REGTECH', 'count': 0},
                {'name': 'SECUDIUM', 'count': 0}
            ],
            'timestamp': datetime.now().isoformat()
        }
    
    def enable_collection(self) -> Dict[str, Any]:
        """수집 시스템 활성화 (동기 버전)"""
        try:
            if self.collection_manager:
                result = self.collection_manager.enable_collection()
                self.logger.info("✅ 수집 시스템 활성화됨")
                return result
            else:
                self.logger.info("✅ 내장 수집 시스템 활성화됨")
                return {'success': True, 'message': '내장 수집 시스템이 활성화되었습니다', 'collection_enabled': True}
        except Exception as e:
            self.logger.error(f"수집 시스템 활성화 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def disable_collection(self) -> Dict[str, Any]:
        """수집 시스템 비활성화 (동기 버전)"""
        try:
            if self.collection_manager:
                result = self.collection_manager.disable_collection()
                self.logger.info("⏹️ 수집 시스템 비활성화됨")
                return result
            else:
                self.logger.info("⏹️ 내장 수집 시스템 비활성화됨")
                return {'success': True, 'message': '내장 수집 시스템이 비활성화되었습니다', 'collection_enabled': False}
        except Exception as e:
            self.logger.error(f"수집 시스템 비활성화 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def trigger_collection(self, source: str = 'all') -> str:
        """수동 수집 트리거"""
        import uuid
        task_id = str(uuid.uuid4())
        self.logger.info(f"Manual collection triggered: {source} (task_id: {task_id})")
        # TODO: Implement actual collection trigger
        return task_id
    
    def trigger_regtech_collection(self, start_date: str = None, end_date: str = None) -> str:
        """REGTECH 수집 트리거"""
        import uuid
        task_id = str(uuid.uuid4())
        self.logger.info(f"REGTECH collection triggered (task_id: {task_id})")
        
        # 수집 로그 추가
        self.add_collection_log('REGTECH', 'collection_started', {
            'task_id': task_id,
            'start_date': start_date,
            'end_date': end_date,
            'is_daily': start_date == end_date if start_date and end_date else False
        })
        
        try:
            # 실제 REGTECH 수집 실행
            self.logger.info(f"Container type: {type(self.container)}")
            self.logger.info(f"Container methods: {[m for m in dir(self.container) if not m.startswith('_')]}")
            regtech_collector = self.container.resolve('regtech_collector')
            if regtech_collector:
                # 백그라운드 수집 시작
                import threading
                def collect_regtech():
                    try:
                        ips = regtech_collector.collect_from_web(start_date=start_date, end_date=end_date)
                        self.logger.info(f"REGTECH collection completed: {len(ips)} IPs collected")
                        
                        # 수집 완료 로그 추가
                        self.add_collection_log('REGTECH', 'collection_completed', {
                            'task_id': task_id,
                            'ips_collected': len(ips),
                            'start_date': start_date,
                            'end_date': end_date,
                            'is_daily': start_date == end_date if start_date and end_date else False
                        })
                        
                        # 수집한 IP를 데이터베이스에 저장
                        if ips and self.blacklist_manager:
                            try:
                                # bulk_import_ips expects a list of dictionaries
                                ips_data = []
                                for ip_entry in ips:
                                    ips_data.append({
                                        'ip': ip_entry.ip_address,
                                        'source': 'REGTECH',
                                        'threat_type': ip_entry.reason,
                                        'country': ip_entry.country,
                                        'reg_date': ip_entry.reg_date,  # 원본 등록일 추가
                                        'reason': ip_entry.reason,  # reason 필드 추가
                                        'threat_level': ip_entry.threat_level,
                                        'confidence': 1.0
                                    })
                                
                                self.logger.info(f"REGTECH: Calling bulk_import_ips with {len(ips_data)} IPs")
                                self.logger.info(f"REGTECH: Sample IP data: {ips_data[:3] if ips_data else 'None'}")  # 샘플 확인
                                result = self.blacklist_manager.bulk_import_ips(ips_data, source='REGTECH')
                                self.logger.info(f"REGTECH: bulk_import_ips result: {result}")
                                
                                if result.get('success'):
                                    self.logger.info(f"REGTECH: {result['imported_count']}개 IP가 데이터베이스에 저장됨")
                                    
                                    # 저장 후 데이터베이스에서 직접 확인
                                    try:
                                        source_counts = self._get_source_counts_from_db()
                                        self.logger.info(f"REGTECH: 저장 후 DB 상태: {source_counts}")
                                    except Exception as verify_e:
                                        self.logger.error(f"REGTECH: DB 확인 실패: {verify_e}")
                                else:
                                    self.logger.error(f"REGTECH: 데이터베이스 저장 실패 - {result.get('error')}")
                            except Exception as e:
                                self.logger.error(f"REGTECH: Error saving to database - {e}")
                                import traceback
                                self.logger.error(f"REGTECH: Traceback - {traceback.format_exc()}")
                        
                    except Exception as e:
                        self.logger.error(f"REGTECH collection failed: {e}")
                        # 수집 실패 로그 추가
                        self.add_collection_log('REGTECH', 'collection_failed', {
                            'task_id': task_id,
                            'error': str(e),
                            'start_date': start_date,
                            'end_date': end_date
                        })
                
                thread = threading.Thread(target=collect_regtech)
                thread.daemon = True
                thread.start()
                self.logger.info(f"REGTECH collection started in background")
            else:
                self.logger.warning("REGTECH collector not available")
                
        except Exception as e:
            self.logger.error(f"Failed to start REGTECH collection: {e}")
            
        return task_id
    
    def trigger_secudium_collection(self) -> str:
        """SECUDIUM 수집 트리거"""
        import uuid
        task_id = str(uuid.uuid4())
        self.logger.info(f"SECUDIUM collection triggered (task_id: {task_id})")
        
        # 수집 로그 추가
        self.add_collection_log('SECUDIUM', 'collection_started', {
            'task_id': task_id
        })
        
        try:
            # 실제 SECUDIUM 수집 실행
            secudium_collector = self.container.resolve('secudium_collector')
            if secudium_collector:
                # 백그라운드 수집 시작
                import threading
                def collect_secudium():
                    try:
                        result = secudium_collector.auto_collect()
                        ips = result.get('ips', []) if result.get('success') else []
                        self.logger.info(f"SECUDIUM collection completed: {len(ips)} IPs collected")
                        
                        # 수집 완료 로그 추가
                        self.add_collection_log('SECUDIUM', 'collection_completed', {
                            'task_id': task_id,
                            'ips_collected': len(ips)
                        })
                        
                        # 수집한 IP를 데이터베이스에 저장
                        if ips and self.blacklist_manager:
                            try:
                                # bulk_import_ips expects a list of dictionaries
                                ips_data = []
                                for ip_entry in ips:
                                    ips_data.append({
                                        'ip': ip_entry.ip_address,
                                        'source': 'SECUDIUM',
                                        'threat_type': ip_entry.reason,
                                        'country': ip_entry.country,
                                        'reg_date': ip_entry.reg_date,  # 원본 등록일 추가
                                        'reason': ip_entry.reason,  # reason 필드 추가
                                        'threat_level': ip_entry.threat_level,
                                        'confidence': 1.0
                                    })
                                
                                self.logger.info(f"SECUDIUM: Calling bulk_import_ips with {len(ips_data)} IPs")
                                result = self.blacklist_manager.bulk_import_ips(ips_data, source='SECUDIUM')
                                if result.get('success'):
                                    self.logger.info(f"SECUDIUM: {result['imported_count']}개 IP가 데이터베이스에 저장됨")
                                else:
                                    self.logger.error(f"SECUDIUM: 데이터베이스 저장 실패 - {result.get('error')}")
                            except Exception as e:
                                self.logger.error(f"SECUDIUM: Error saving to database - {e}")
                                import traceback
                                self.logger.error(f"SECUDIUM: Traceback - {traceback.format_exc()}")
                        
                    except Exception as e:
                        self.logger.error(f"SECUDIUM collection failed: {e}")
                        # 수집 실패 로그 추가
                        self.add_collection_log('SECUDIUM', 'collection_failed', {
                            'task_id': task_id,
                            'error': str(e)
                        })
                
                thread = threading.Thread(target=collect_secudium)
                thread.daemon = True
                thread.start()
                self.logger.info(f"SECUDIUM collection started in background")
            else:
                self.logger.warning("SECUDIUM collector not available")
                
        except Exception as e:
            self.logger.error(f"Failed to start SECUDIUM collection: {e}")
            
        return task_id
    
    def get_enhanced_blacklist(self, page: int = 1, per_page: int = 50, include_metadata: bool = True, source_filter: str = None) -> Dict[str, Any]:
        """향상된 블랙리스트 조회"""
        try:
            ips = self.get_active_blacklist_ips()
            
            # Simple pagination
            start = (page - 1) * per_page
            end = start + per_page
            paginated_ips = ips[start:end]
            
            # Add metadata if requested
            if include_metadata:
                data = [
                    {
                        'ip': ip,
                        'source': 'unknown',
                        'added_date': datetime.now().isoformat(),
                        'threat_level': 'high',
                        'category': 'malicious'
                    }
                    for ip in paginated_ips
                ]
            else:
                data = paginated_ips
            
            return {
                'page': page,
                'per_page': per_page,
                'total': len(ips),
                'pages': (len(ips) + per_page - 1) // per_page,
                'data': data,
                'metadata_included': include_metadata
            }
        except Exception as e:
            self.logger.error(f"Failed to get enhanced blacklist: {e}")
            return {
                'page': page,
                'per_page': per_page,
                'total': 0,
                'pages': 0,
                'data': [],
                'error': str(e)
            }
    
    def get_monthly_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """월별 통계 조회"""
        try:
            # Get stats from blacklist manager if available
            if self.blacklist_manager and hasattr(self.blacklist_manager, 'get_stats_for_period'):
                stats = self.blacklist_manager.get_stats_for_period(start_date, end_date)
                return stats
            
            # Fallback to basic stats
            total_ips = len(self.get_active_blacklist_ips())
            return {
                'total_ips': total_ips,
                'first_detection': start_date,
                'last_detection': end_date,
                'sources': {
                    'REGTECH': 0,
                    'SECUDIUM': 0
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get monthly stats: {e}")
            return {
                'total_ips': 0,
                'first_detection': None,
                'last_detection': None,
                'sources': {}
            }
    
    def cleanup_old_data(self, cutoff_date: str) -> Dict[str, Any]:
        """오래된 데이터 정리"""
        try:
            # Use blacklist manager's cleanup function if available
            if self.blacklist_manager and hasattr(self.blacklist_manager, 'cleanup_old_data'):
                result = self.blacklist_manager.cleanup_old_data(cutoff_date)
                return result
            
            # Fallback response
            return {
                'success': True,
                'deleted_count': 0,
                'message': 'Cleanup function not available in current configuration'
            }
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            return {
                'success': False,
                'deleted_count': 0,
                'message': str(e)
            }

# 전역 서비스 인스턴스
_unified_service = None

def get_unified_service() -> UnifiedBlacklistService:
    """통합 서비스 인스턴스 반환 (싱글톤)"""
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedBlacklistService()
    return _unified_service