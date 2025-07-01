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
        
        # 수집 상태 관리 (메모리)
        self.collection_enabled = True
        self.daily_collection_enabled = False
        
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
        
        # 최초 실행 시 자동 수집 수행
        self._check_and_perform_initial_collection()
        
    def _check_and_perform_initial_collection(self):
        """최초 실행 시 자동 수집 수행"""
        try:
            if self.collection_manager and self.collection_manager.is_initial_collection_needed():
                self.logger.info("🔥 최초 실행 감지 - 자동 수집 시작...")
                
                # 수집 활성화 (이미 활성화되어 있지만 확실히)
                if not self.collection_manager.collection_enabled:
                    self.collection_manager.enable_collection()
                
                # 비동기 작업을 동기적으로 실행
                import asyncio
                import threading
                
                def run_initial_collection():
                    try:
                        # 새 이벤트 루프 생성
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        # 오늘 날짜로 수집
                        today = datetime.now()
                        start_date = (today - timedelta(days=90)).strftime('%Y%m%d')
                        end_date = today.strftime('%Y%m%d')
                        
                        self.logger.info(f"📅 최초 수집 기간: {start_date} ~ {end_date}")
                        
                        # REGTECH 수집
                        self.logger.info("🔄 REGTECH 최초 수집 시작...")
                        regtech_result = self.collection_manager.trigger_regtech_collection(start_date, end_date)
                        if regtech_result.get('success'):
                            self.logger.info(f"✅ REGTECH 수집 성공: {regtech_result.get('message', '')}")
                        else:
                            self.logger.warning(f"⚠️ REGTECH 수집 실패: {regtech_result.get('message', '')}")
                        
                        # SECUDIUM 수집
                        self.logger.info("🔄 SECUDIUM 최초 수집 시작...")
                        secudium_result = self.collection_manager.trigger_secudium_collection()
                        if secudium_result.get('success'):
                            self.logger.info(f"✅ SECUDIUM 수집 성공: {secudium_result.get('message', '')}")
                        else:
                            self.logger.warning(f"⚠️ SECUDIUM 수집 실패: {secudium_result.get('message', '')}")
                        
                        # 최초 수집 완료 표시
                        self.collection_manager.mark_initial_collection_done()
                        self.logger.info("🎉 최초 수집 완료!")
                        
                        # 수집 로그 추가
                        self.add_collection_log('system', 'initial_collection_complete', {
                            'regtech': regtech_result,
                            'secudium': secudium_result
                        })
                        
                    except Exception as e:
                        self.logger.error(f"최초 수집 중 오류 발생: {e}")
                        import traceback
                        self.logger.error(traceback.format_exc())
                
                # 백그라운드 스레드에서 실행
                collection_thread = threading.Thread(target=run_initial_collection)
                collection_thread.daemon = True
                collection_thread.start()
                
        except Exception as e:
            self.logger.error(f"최초 수집 체크 중 오류: {e}")
    
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
    
    def clear_all_database_data(self) -> Dict[str, Any]:
        """모든 데이터베이스 데이터 삭제"""
        try:
            # Use blacklist_manager to clear data
            if self.blacklist_manager:
                self.blacklist_manager.clear_all()
                return {
                    'success': True,
                    'message': 'All database data cleared'
                }
            else:
                return {
                    'success': False,
                    'error': 'Blacklist manager not available'
                }
        except Exception as e:
            self.logger.error(f"Failed to clear database data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def set_daily_collection_config(self, enabled: bool, strategy: str, collection_days: int) -> Dict[str, Any]:
        """일일 수집 설정"""
        try:
            self.daily_collection_enabled = enabled
            self.add_collection_log('system', 'daily_collection_config', {
                'enabled': enabled,
                'strategy': strategy,
                'collection_days': collection_days
            })
            return {
                'success': True,
                'enabled': enabled,
                'strategy': strategy,
                'collection_days': collection_days
            }
        except Exception as e:
            self.logger.error(f"Failed to set daily collection config: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Removed duplicate clear_all_data method - using the comprehensive one at line 1431
    
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
    
    def get_blacklist_summary(self) -> Dict[str, Any]:
        """블랙리스트 요약 정보 반환"""
        try:
            # Get system health which contains the summary info
            health = self.get_system_health()
            return {
                'total_ips': health.get('total_ips', 0),
                'active_ips': health.get('active_ips', 0),
                'regtech_count': health.get('regtech_count', 0),
                'secudium_count': health.get('secudium_count', 0),
                'public_count': health.get('public_count', 0),
                'status': health.get('status', 'unknown'),
                'last_update': health.get('last_update', None)
            }
        except Exception as e:
            self.logger.error(f"Failed to get blacklist summary: {e}")
            return {
                'total_ips': 0,
                'active_ips': 0,
                'regtech_count': 0,
                'secudium_count': 0,
                'public_count': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def get_collection_status(self) -> Dict[str, Any]:
        """수집 시스템 상태 조회"""
        try:
            # 메모리 상태와 DB 통계 조합
            stats = self.get_blacklist_summary()
            
            return {
                'collection_enabled': self.collection_enabled,
                'daily_collection_enabled': self.daily_collection_enabled,
                'status': 'active' if self.collection_enabled else 'inactive',
                'sources': {
                    'regtech': {
                        'enabled': True,
                        'status': 'ready',
                        'last_collection': None
                    },
                    'secudium': {
                        'enabled': True,
                        'status': 'ready', 
                        'last_collection': None
                    }
                },
                'stats': {
                    'total_ips': stats.get('total_ips', 0),
                    'active_ips': stats.get('active_ips', 0),
                    'regtech_count': stats.get('regtech_count', 0),
                    'secudium_count': stats.get('secudium_count', 0),
                    'today_collected': 0
                },
                'last_collection': None,
                'last_enabled_at': None,
                'last_disabled_at': None
            }
        except Exception as e:
            self.logger.error(f"수집 상태 조회 실패: {e}")
            return {
                'collection_enabled': False,
                'daily_collection_enabled': False,
                'status': 'error',
                'error': str(e),
                'sources': {},
                'stats': {
                    'total_ips': 0,
                    'active_ips': 0,
                    'regtech_count': 0,
                    'secudium_count': 0,
                    'today_collected': 0
                }
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
        current_time = datetime.now()
        
        # 상세한 메시지 생성
        detailed_message = self._create_detailed_log_message(source, action, details, current_time)
        
        log_entry = {
            'timestamp': current_time.isoformat(),
            'source': source,
            'action': action,
            'details': details or {},
            'message': detailed_message  # 상세 메시지 추가
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
            
        # 콘솔에도 출력 (상세 메시지 사용)
        self.logger.info(f"📝 {detailed_message}")
    
    def _create_detailed_log_message(self, source: str, action: str, details: Dict[str, Any], timestamp: datetime) -> str:
        """상세한 로그 메시지 생성 - 사용자 요청 형식: '2020-00.00 regtech/secudium(에 따라서) **개 아이피 수집됨'"""
        
        # 날짜 형식 생성
        date_str = timestamp.strftime('%Y-%m.%d')
        
        # 소스명 정리
        source_name = source.upper()
        if source_name == 'REGTECH':
            source_display = 'REGTECH'
        elif source_name == 'SECUDIUM':
            source_display = 'SECUDIUM'
        else:
            source_display = source_name
            
        # 액션에 따른 메시지 생성
        if action == 'collection_complete':
            ip_count = details.get('ip_count', 0) if details else 0
            message = f"{date_str} {source_display}에서 {ip_count}개 아이피 수집됨"
            
        elif action == 'collection_start':
            message = f"{date_str} {source_display} 수집 시작"
            
        elif action == 'collection_failed':
            error_msg = details.get('error', '알 수 없는 오류') if details else '알 수 없는 오류'
            message = f"{date_str} {source_display} 수집 실패: {error_msg}"
            
        elif action == 'collection_enabled':
            message = f"{date_str} {source_display} 수집 활성화됨"
            
        elif action == 'collection_disabled':
            message = f"{date_str} {source_display} 수집 비활성화됨"
            
        elif action == 'collection_triggered':
            message = f"{date_str} {source_display} 수동 수집 트리거됨"
            
        elif action == 'collection_progress':
            progress_msg = details.get('message', '진행 중') if details else '진행 중'
            message = f"{date_str} {source_display} 진행: {progress_msg}"
            
        else:
            # 기본 형식
            message = f"{date_str} {source_display}: {action}"
            
        return message
    
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
            # 데이터베이스 경로 결정 - 설정에서 가져오기
            db_path = None
            if self.blacklist_manager and hasattr(self.blacklist_manager, 'db_path'):
                db_path = self.blacklist_manager.db_path
            else:
                # 설정에서 데이터베이스 URI 가져오기
                from src.config.settings import settings
                
                db_uri = settings.database_uri
                # sqlite:///path/to/db.db 형식에서 경로 추출
                if db_uri.startswith('sqlite:///'):
                    db_path = db_uri[10:]  # 'sqlite:///' 제거
                elif db_uri.startswith('sqlite://'):
                    db_path = db_uri[9:]   # 'sqlite://' 제거
                else:
                    # Fallback - 설정에서 instance 디렉토리 사용
                    db_path = str(settings.instance_dir / 'blacklist.db')
            
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
            # 데이터베이스 경로 결정 - 설정에서 가져오기
            db_path = None
            if self.blacklist_manager and hasattr(self.blacklist_manager, 'db_path'):
                db_path = self.blacklist_manager.db_path
            else:
                # 설정에서 데이터베이스 URI 가져오기
                from src.config.settings import settings
                import re
                
                db_uri = settings.database_uri
                # sqlite:///path/to/db.db 형식에서 경로 추출
                if db_uri.startswith('sqlite:///'):
                    db_path = db_uri[10:]  # 'sqlite:///' 제거
                elif db_uri.startswith('sqlite://'):
                    db_path = db_uri[9:]   # 'sqlite://' 제거
                else:
                    # Fallback - 설정에서 instance 디렉토리 사용
                    db_path = str(settings.instance_dir / 'blacklist.db')
                    
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
            # 데이터베이스 경로 결정 - 설정에서 가져오기
            db_path = None
            if self.blacklist_manager and hasattr(self.blacklist_manager, 'db_path'):
                db_path = self.blacklist_manager.db_path
            else:
                # 설정에서 데이터베이스 URI 가져오기
                from src.config.settings import settings
                
                db_uri = settings.database_uri
                # sqlite:///path/to/db.db 형식에서 경로 추출
                if db_uri.startswith('sqlite:///'):
                    db_path = db_uri[10:]  # 'sqlite:///' 제거
                elif db_uri.startswith('sqlite://'):
                    db_path = db_uri[9:]   # 'sqlite://' 제거
                else:
                    # Fallback - 설정에서 instance 디렉토리 사용
                    db_path = str(settings.instance_dir / 'blacklist.db')
            
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
    
    def get_daily_stats(self, days: int = 30) -> list:
        """일별 통계 반환"""
        from datetime import timedelta
        
        stats = []
        end_date = datetime.now()
        
        for i in range(days):
            date = end_date - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            # Get stats for this specific date
            daily_stat = {
                'date': date_str,
                'total_ips': 0,
                'regtech_count': 0,
                'secudium_count': 0,
                'public_count': 0,
                'new_ips': 0,
                'expired_ips': 0
            }
            
            # Try to get data from database
            if self.blacklist_manager:
                try:
                    conn = sqlite3.connect(self.blacklist_manager.db_path)
                    cursor = conn.cursor()
                    
                    # Count total IPs by source for this date (using detection_date - 실제 등록일)
                    cursor.execute("""
                        SELECT source, COUNT(*) 
                        FROM blacklist_ip 
                        WHERE DATE(detection_date) = ?
                        GROUP BY source
                    """, (date_str,))
                    
                    for row in cursor.fetchall():
                        source = row[0]
                        count = row[1]
                        if source == 'REGTECH':
                            daily_stat['regtech_count'] = count
                        elif source == 'SECUDIUM':
                            daily_stat['secudium_count'] = count
                        elif source == 'PUBLIC':
                            daily_stat['public_count'] = count
                        daily_stat['total_ips'] += count
                    
                    # Count new IPs for this date (using detection_date - 실제 등록일)
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM blacklist_ip 
                        WHERE DATE(detection_date) = ?
                    """, (date_str,))
                    daily_stat['new_ips'] = cursor.fetchone()[0]
                    
                    conn.close()
                except Exception as e:
                    self.logger.warning(f"Failed to get daily stats for {date_str}: {e}")
            
            # Check collection logs for this date
            for log in self.collection_logs:
                if log.get('timestamp', '').startswith(date_str):
                    if 'collection_completed' in log.get('action', ''):
                        details = log.get('details', {})
                        if details.get('ip_count', 0) > 0:
                            daily_stat['total_ips'] = max(daily_stat['total_ips'], details['ip_count'])
                            source = log.get('source', '').upper()
                            if source == 'REGTECH':
                                daily_stat['regtech_count'] = details['ip_count']
                            elif source == 'SECUDIUM':
                                daily_stat['secudium_count'] = details['ip_count']
            
            stats.append(daily_stat)
        
        # Reverse to show newest first
        return list(reversed(stats))
    
    def enable_collection(self) -> Dict[str, Any]:
        """수집 시스템 활성화 (동기 버전)"""
        try:
            # 기존 데이터 클리어
            self.clear_all_database_data()
            
            # 메모리에서 수집 상태 활성화
            self.collection_enabled = True
            
            self.logger.info("✅ 수집 시스템 활성화됨 (기존 데이터 클리어됨)")
            return {
                'success': True, 
                'message': '수집 시스템이 활성화되었습니다. 기존 데이터가 클리어되었습니다.', 
                'collection_enabled': True
            }
        except Exception as e:
            self.logger.error(f"수집 시스템 활성화 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def disable_collection(self) -> Dict[str, Any]:
        """수집 시스템 비활성화 (동기 버전)"""
        try:
            # 메모리에서 수집 상태 비활성화
            self.collection_enabled = False
            
            self.logger.info("⏹️ 수집 시스템 비활성화됨")
            return {
                'success': True, 
                'message': '수집 시스템이 비활성화되었습니다', 
                'collection_enabled': False
            }
        except Exception as e:
            self.logger.error(f"수집 시스템 비활성화 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def enable_daily_collection(self) -> Dict[str, Any]:
        """일일 자동 수집 활성화"""
        try:
            # 메모리에서 일일 수집 상태 활성화
            self.daily_collection_enabled = True
            
            self.logger.info("📅 일일 자동 수집 활성화됨")
            return {
                'success': True, 
                'message': '일일 자동 수집이 활성화되었습니다', 
                'daily_collection_enabled': True
            }
        except Exception as e:
            self.logger.error(f"일일 자동 수집 활성화 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def disable_daily_collection(self) -> Dict[str, Any]:
        """일일 자동 수집 비활성화"""
        try:
            # 메모리에서 일일 수집 상태 비활성화
            self.daily_collection_enabled = False
            
            self.logger.info("📅 일일 자동 수집 비활성화됨")
            return {
                'success': True, 
                'message': '일일 자동 수집이 비활성화되었습니다', 
                'daily_collection_enabled': False
            }
        except Exception as e:
            self.logger.error(f"일일 자동 수집 비활성화 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def trigger_collection(self, source: str = 'all') -> str:
        """수동 수집 트리거"""
        import uuid
        task_id = str(uuid.uuid4())
        self.logger.info(f"Manual collection triggered: {source} (task_id: {task_id})")
        # TODO: Implement actual collection trigger based on source parameter
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
    
    def clear_all_data(self) -> Dict[str, Any]:
        """전체 데이터베이스 클리어 - 모든 테이블의 데이터 삭제 및 ID 시퀀스 리셋"""
        try:
            # 데이터베이스 경로 결정
            db_path = None
            if self.blacklist_manager and hasattr(self.blacklist_manager, 'db_path'):
                db_path = self.blacklist_manager.db_path
            else:
                from src.config.settings import settings
                db_uri = settings.database_uri
                if db_uri.startswith('sqlite:///'):
                    db_path = db_uri[10:]
                elif db_uri.startswith('sqlite://'):
                    db_path = db_uri[9:]
                else:
                    db_path = str(settings.instance_dir / 'blacklist.db')
            
            if not db_path or not os.path.exists(db_path):
                return {
                    'success': False,
                    'error': 'Database file not found'
                }
            
            import sqlite3
            
            # 먼저 데이터 삭제 작업 수행
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 모든 테이블의 데이터 개수 확인
                table_counts = {}
                tables_to_clear = ['blacklist_ip', 'ip_detection', 'collection_logs']
                
                for table in tables_to_clear:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        table_counts[table] = count
                    except sqlite3.OperationalError:
                        # 테이블이 존재하지 않으면 0으로 설정
                        table_counts[table] = 0
                
                total_deleted = sum(table_counts.values())
                
                # 모든 테이블 데이터 삭제
                for table in tables_to_clear:
                    try:
                        cursor.execute(f"DELETE FROM {table}")
                        self.logger.info(f"Cleared {table_counts.get(table, 0)} records from {table}")
                    except sqlite3.OperationalError as e:
                        self.logger.warning(f"Could not clear table {table}: {e}")
                
                # SQLite 자동 증가 시퀀스 리셋
                for table in tables_to_clear:
                    try:
                        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                        self.logger.info(f"Reset auto-increment sequence for {table}")
                    except sqlite3.OperationalError:
                        # sqlite_sequence 테이블이 없거나 해당 테이블에 항목이 없으면 무시
                        pass
                
                conn.commit()
            
            # VACUUM은 별도 연결에서 실행 (자동 커밋 모드)
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("VACUUM")
                conn.close()
                self.logger.info("Database optimized with VACUUM")
            except Exception as e:
                self.logger.warning(f"VACUUM failed: {e}")
                
                # 메모리 캐시도 클리어
                if hasattr(self, 'collection_logs'):
                    self.collection_logs = []
                
                # 통계 캐시 클리어 (있다면)
                if self.cache:
                    try:
                        # 캐시의 모든 blacklist 관련 키 클리어
                        self.cache.clear()
                        self.logger.info("Cache cleared")
                    except Exception as e:
                        self.logger.warning(f"Failed to clear cache: {e}")
                
                self.logger.info(f"✅ 데이터베이스 완전 클리어 완료: {total_deleted}개 레코드 삭제, ID 시퀀스 리셋")
                
                # 수집 로그 추가
                self.add_collection_log('SYSTEM', 'database_cleared', {
                    'total_deleted': total_deleted,
                    'cleared_tables': list(table_counts.keys()),
                    'table_counts': table_counts
                })
                
                return {
                    'success': True,
                    'message': f'데이터베이스가 성공적으로 클리어되었습니다.',
                    'cleared_tables': list(table_counts.keys()),
                    'total_deleted': total_deleted,
                    'table_counts': table_counts,
                    'id_sequences_reset': True,
                    'cache_cleared': self.cache is not None,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"데이터베이스 클리어 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'데이터베이스 클리어 중 오류 발생: {e}'
            }
    
    # === 일일 수집 설정 관리 ===
    
    def set_daily_collection_config(self, enabled: bool, strategy: str = None, collection_days: int = 3) -> Dict[str, Any]:
        """일일 수집 설정 저장"""
        try:
            # 설정을 파일이나 데이터베이스에 저장
            config = {
                'enabled': enabled,
                'strategy': strategy,
                'collection_days': collection_days,
                'updated_at': datetime.now().isoformat()
            }
            
            # 설정을 JSON 파일로 저장 (간단한 구현)
            config_path = 'daily_collection_config.json'
            import json
            try:
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                self.logger.info(f"일일 수집 설정 저장: {config}")
            except Exception as e:
                self.logger.warning(f"설정 파일 저장 실패: {e}")
            
            # 메모리에도 저장
            if not hasattr(self, '_daily_config'):
                self._daily_config = {}
            self._daily_config.update(config)
            
            # 수집 로그 추가
            action = 'daily_collection_enabled' if enabled else 'daily_collection_disabled'
            self.add_collection_log('SYSTEM', action, {
                'strategy': strategy,
                'collection_days': collection_days,
                'enabled': enabled
            })
            
            return {
                'success': True,
                'message': f'일일 수집 설정이 {"활성화" if enabled else "비활성화"}되었습니다.',
                'config': config
            }
            
        except Exception as e:
            self.logger.error(f"일일 수집 설정 저장 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_daily_collection_config(self) -> Dict[str, Any]:
        """일일 수집 설정 조회"""
        try:
            # 메모리에서 먼저 확인
            if hasattr(self, '_daily_config') and self._daily_config:
                return self._daily_config
            
            # 파일에서 로드
            config_path = 'daily_collection_config.json'
            import json
            import os
            
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    self._daily_config = config
                    return config
                except Exception as e:
                    self.logger.warning(f"설정 파일 로드 실패: {e}")
            
            # 기본 설정 반환
            default_config = {
                'enabled': False,
                'strategy': 'disabled',
                'collection_days': 0,
                'updated_at': datetime.now().isoformat()
            }
            
            self._daily_config = default_config
            return default_config
            
        except Exception as e:
            self.logger.error(f"일일 수집 설정 조회 실패: {e}")
            return {
                'enabled': False,
                'strategy': 'disabled',
                'collection_days': 0,
                'error': str(e)
            }
    
    def is_daily_collection_enabled(self) -> bool:
        """일일 수집이 활성화되어 있는지 확인"""
        config = self.get_daily_collection_config()
        return config.get('enabled', False)
    
    def get_daily_collection_strategy(self) -> str:
        """일일 수집 전략 조회"""
        config = self.get_daily_collection_config()
        return config.get('strategy', 'disabled')
    
    # === 자동 수집 시스템 지원 메서드 ===
    
    def get_daily_collection_stats(self) -> list:
        """날짜별 수집 통계 반환"""
        try:
            db_path = os.path.join('/app' if os.path.exists('/app') else '.', 'instance/blacklist.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 최근 30일간의 날짜별 수집 통계
            query = """
            SELECT 
                DATE(detection_date) as date,
                COUNT(*) as count,
                source
            FROM blacklist_ip 
            WHERE detection_date >= DATE('now', '-30 days')
            GROUP BY DATE(detection_date), source
            ORDER BY date DESC
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            
            # 날짜별로 그룹화
            stats_dict = {}
            for row in rows:
                date, count, source = row
                if date not in stats_dict:
                    stats_dict[date] = {'date': date, 'count': 0, 'sources': {}}
                stats_dict[date]['count'] += count
                stats_dict[date]['sources'][source] = count
            
            # 리스트로 변환하여 반환
            return list(stats_dict.values())
            
        except Exception as e:
            self.logger.error(f"Daily collection stats error: {e}")
            return []
    
    def get_source_statistics(self) -> dict:
        """소스별 통계 반환"""
        try:
            db_path = os.path.join('/app' if os.path.exists('/app') else '.', 'instance/blacklist.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 소스별 총 개수
            query = """
            SELECT 
                source,
                COUNT(*) as total,
                MIN(detection_date) as first_detection,
                MAX(detection_date) as last_detection,
                COUNT(DISTINCT DATE(detection_date)) as collection_days
            FROM blacklist_ip 
            GROUP BY source
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            
            stats = {}
            for row in rows:
                source, total, first_detection, last_detection, collection_days = row
                stats[source.lower()] = {
                    'total': total,
                    'first_detection': first_detection,
                    'last_detection': last_detection,
                    'collection_days': collection_days
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Source statistics error: {e}")
            return {}
    
    def get_collection_intervals(self) -> dict:
        """현재 수집 간격 설정 반환"""
        try:
            # 설정 파일 경로
            config_path = os.path.join('/app' if os.path.exists('/app') else '.', 'instance/collection_intervals.json')
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                return config
            else:
                # 기본값
                default_config = {
                    'regtech_days': 90,  # 3개월
                    'secudium_days': 3,  # 3일
                    'updated_at': datetime.now().isoformat()
                }
                # 기본값을 파일로 저장
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
                
        except Exception as e:
            self.logger.error(f"Get collection intervals error: {e}")
            return {
                'regtech_days': 90,
                'secudium_days': 3,
                'error': str(e)
            }
    
    def update_collection_intervals(self, regtech_days: int, secudium_days: int) -> dict:
        """수집 간격 설정 업데이트"""
        try:
            config = {
                'regtech_days': regtech_days,
                'secudium_days': secudium_days,
                'updated_at': datetime.now().isoformat()
            }
            
            # 설정 파일 저장
            config_path = os.path.join('/app' if os.path.exists('/app') else '.', 'instance/collection_intervals.json')
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.logger.info(f"Collection intervals updated: REGTECH={regtech_days}days, SECUDIUM={secudium_days}days")
            
            return {
                'success': True,
                'regtech_days': regtech_days,
                'secudium_days': secudium_days,
                'updated_at': config['updated_at']
            }
            
        except Exception as e:
            self.logger.error(f"Update collection intervals error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_missing_dates_for_collection(self, source: str, days_back: int) -> list:
        """수집이 누락된 날짜 목록 반환"""
        try:
            from datetime import datetime, timedelta
            
            db_path = os.path.join('/app' if os.path.exists('/app') else '.', 'instance/blacklist.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 지정된 기간 내에서 수집된 날짜들 조회
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            query = """
            SELECT DISTINCT DATE(detection_date) as date
            FROM blacklist_ip 
            WHERE source = ? AND detection_date >= ?
            ORDER BY date DESC
            """
            
            cursor.execute(query, (source.upper(), start_date))
            collected_dates = set(row[0] for row in cursor.fetchall())
            conn.close()
            
            # 전체 날짜 범위에서 누락된 날짜 찾기
            missing_dates = []
            current_date = datetime.now()
            
            for i in range(days_back):
                check_date = (current_date - timedelta(days=i)).strftime('%Y-%m-%d')
                if check_date not in collected_dates:
                    missing_dates.append(check_date)
            
            return missing_dates
            
        except Exception as e:
            self.logger.error(f"Get missing dates error: {e}")
            return []
    
    def enable_collection(self) -> dict:
        """수집 활성화"""
        try:
            # CollectionManager를 통해 수집 활성화
            collection_manager = self.container.get('collection_manager')
            if not collection_manager:
                return {
                    'success': False,
                    'error': 'Collection manager not available'
                }
            
            # 수집 활성화
            result = collection_manager.enable_collection()
            
            # 로그 추가
            self.add_collection_log('system', 'collection_enabled', {
                'message': '수집이 활성화되었습니다',
                'timestamp': datetime.now().isoformat()
            })
            
            self.logger.info("Collection enabled successfully")
            
            return {
                'success': True,
                'message': '수집이 활성화되었습니다',
                'status': 'enabled',
                'enabled_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Enable collection error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '수집 활성화 실패'
            }
    
    def disable_collection(self) -> dict:
        """수집 비활성화"""
        try:
            # CollectionManager를 통해 수집 비활성화
            collection_manager = self.container.get('collection_manager')
            if not collection_manager:
                return {
                    'success': False,
                    'error': 'Collection manager not available'
                }
            
            # 수집 비활성화
            result = collection_manager.disable_collection()
            
            # 로그 추가
            self.add_collection_log('system', 'collection_disabled', {
                'message': '수집이 비활성화되었습니다',
                'timestamp': datetime.now().isoformat()
            })
            
            self.logger.info("Collection disabled successfully")
            
            return {
                'success': True,
                'message': '수집이 비활성화되었습니다',
                'status': 'disabled',
                'disabled_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Disable collection error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '수집 비활성화 실패'
            }
    
    def trigger_regtech_collection(self, start_date: str = None, end_date: str = None) -> dict:
        """REGTECH 수집 트리거 (데이터베이스 저장 포함)"""
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
            regtech_collector = self.container.resolve('regtech_collector')
            if not regtech_collector:
                self.logger.error("REGTECH collector not available")
                return {
                    'success': False,
                    'error': 'REGTECH collector not available',
                    'message': 'REGTECH 수집기를 찾을 수 없습니다'
                }
            
            # 실제 수집 실행 (동기적으로 처리)
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
                        # REGTECH 데이터를 모든 필드 포함해서 저장
                        ips_data = []
                        for ip_entry in ips:
                            # IP 주소 추출
                            ip_addr = None
                            if hasattr(ip_entry, 'ip_address'):
                                ip_addr = ip_entry.ip_address
                            elif hasattr(ip_entry, 'ip'):
                                ip_addr = ip_entry.ip
                            elif isinstance(ip_entry, dict):
                                ip_addr = ip_entry.get('ip_address') or ip_entry.get('ip')
                            elif isinstance(ip_entry, str):
                                ip_addr = ip_entry
                                
                            if not ip_addr:
                                continue
                                
                            # REGTECH 모든 필드 저장 (스키마에 맞게)
                            ips_data.append({
                                'ip': ip_addr,
                                'ip_address': ip_addr,  # 원본 필드도 저장
                                'source': 'REGTECH',
                                'reason': getattr(ip_entry, 'reason', None),
                                'country': getattr(ip_entry, 'country', None),
                                'threat_level': getattr(ip_entry, 'threat_level', None),
                                'as_name': getattr(ip_entry, 'as_name', None),
                                'city': getattr(ip_entry, 'city', None),
                                'reg_date': getattr(ip_entry, 'reg_date', None),
                                'attack_type': getattr(ip_entry, 'reason', None),  # reason을 attack_type으로도 저장
                                'detection_date': getattr(ip_entry, 'reg_date', None)  # reg_date를 detection_date로도 저장
                            })
                        
                        self.logger.info(f"REGTECH: Calling bulk_import_ips with {len(ips_data)} IPs")
                        self.logger.info(f"REGTECH: Sample IP data: {ips_data[:3] if ips_data else 'None'}")
                        
                        # 실제로 bulk_import_ips 호출하기 전에 blacklist_manager 확인
                        if not self.blacklist_manager:
                            self.logger.error("REGTECH: blacklist_manager is None!")
                            return {
                                'success': False,
                                'error': 'blacklist_manager not available',
                                'message': 'REGTECH 수집 실패: blacklist_manager 없음'
                            }
                        
                        self.logger.info(f"REGTECH: blacklist_manager type: {type(self.blacklist_manager)}")
                        result = self.blacklist_manager.bulk_import_ips(ips_data, source='REGTECH')
                        self.logger.info(f"REGTECH: bulk_import_ips result: {result}")
                        self.logger.info(f"REGTECH: result type: {type(result)}")
                        
                        if result.get('success'):
                            self.logger.info(f"REGTECH: {result['imported_count']}개 IP가 데이터베이스에 저장됨")
                            
                            # 저장 후 데이터베이스에서 직접 확인
                            try:
                                source_counts = self._get_source_counts_from_db()
                                self.logger.info(f"REGTECH: 저장 후 DB 상태: {source_counts}")
                            except Exception as verify_e:
                                self.logger.error(f"REGTECH: DB 확인 실패: {verify_e}")
                                
                            return {
                                'success': True,
                                'ip_count': len(ips),
                                'imported_count': result.get('imported_count', 0),
                                'message': f'REGTECH 수집 완료: {len(ips)}개 IP 수집됨'
                            }
                        else:
                            self.logger.error(f"REGTECH: 데이터베이스 저장 실패 - {result.get('error')}")
                            return {
                                'success': False,
                                'error': result.get('error'),
                                'message': 'REGTECH 데이터베이스 저장 실패'
                            }
                    except Exception as e:
                        self.logger.error(f"REGTECH 데이터 저장 중 오류: {e}")
                        return {
                            'success': False,
                            'error': str(e),
                            'message': 'REGTECH 데이터 저장 실패'
                        }
                else:
                    return {
                        'success': True,
                        'ip_count': len(ips) if ips else 0,
                        'message': f'REGTECH 수집 완료: {len(ips) if ips else 0}개 IP 수집됨 (저장 불가)'
                    }
                    
            except Exception as e:
                self.logger.error(f"REGTECH 수집 실행 중 오류: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'message': 'REGTECH 수집 실행 실패'
                }
                
        except Exception as e:
            self.logger.error(f"REGTECH trigger error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'REGTECH 수집 트리거 실패'
            }
    
    def trigger_secudium_collection(self) -> dict:
        """SECUDIUM 수집 트리거"""
        try:
            # SECUDIUM 수집기 가져오기
            secudium_collector = self.container.resolve('secudium_collector')
            if not secudium_collector:
                return {
                    'success': False,
                    'error': 'SECUDIUM collector not available'
                }
            
            # 수집 시작 로그
            self.add_collection_log('secudium', 'collection_start', {
                'triggered_by': 'manual',
                'start_time': datetime.now().isoformat()
            })
            
            # 수집 실행
            try:
                # collect_from_web()은 List[BlacklistEntry]를 반환함
                entries = secudium_collector.collect_from_web()
                
                if entries:  # 리스트가 비어있지 않은 경우
                    ip_count = len(entries)
                    
                    # 수집한 IP를 데이터베이스에 저장
                    if self.blacklist_manager:
                        try:
                            # bulk_import_ips expects a list of dictionaries
                            ips_data = []
                            for entry in entries:
                                ips_data.append({
                                    'ip': entry.ip_address,
                                    'source': 'SECUDIUM',
                                    'attack_type': entry.reason,
                                    'threat_type': entry.reason,
                                    'country': entry.country,
                                    'reg_date': entry.reg_date,  # 원본 등록일
                                    'detection_date': entry.reg_date,  # detection_date 추가
                                    'reason': entry.reason,
                                    'threat_level': entry.threat_level,
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
                    
                    # 수집 완료 로그
                    self.add_collection_log('secudium', 'collection_complete', {
                        'ip_count': ip_count,
                        'triggered_by': 'manual',
                        'end_time': datetime.now().isoformat()
                    })
                    
                    return {
                        'success': True,
                        'message': f'SECUDIUM 수집 완료: {ip_count}개 IP 수집됨',
                        'ip_count': ip_count,
                        'source': 'secudium'
                    }
                else:
                    self.add_collection_log('secudium', 'collection_failed', {
                        'error': 'No IPs collected',
                        'triggered_by': 'manual'
                    })
                    
                    return {
                        'success': False,
                        'error': 'No IPs collected',
                        'message': 'SECUDIUM 수집 실패: IP를 찾을 수 없습니다'
                    }
                    
            except Exception as e:
                self.add_collection_log('secudium', 'collection_failed', {
                    'error': str(e),
                    'triggered_by': 'manual'
                })
                raise e
            
        except Exception as e:
            self.logger.error(f"SECUDIUM trigger error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'SECUDIUM 수집 트리거 실패'
            }

# 전역 서비스 인스턴스
_unified_service = None

def get_unified_service() -> UnifiedBlacklistService:
    """통합 서비스 인스턴스 반환 (싱글톤)"""
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedBlacklistService()
    return _unified_service