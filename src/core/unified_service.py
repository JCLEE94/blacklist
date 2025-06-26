#!/usr/bin/env python3
"""
통합 블랙리스트 관리 서비스
모든 블랙리스트 운영을 하나로 통합한 서비스
"""
import os
import logging
import asyncio
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
                self.logger.info("🔄 주기적 데이터 수집 시작...")
                
                # 모든 소스에서 데이터 수집
                result = await self.collect_all_data()
                
                if result.get('success'):
                    total_collected = sum(r.get('total_collected', 0) for r in result.get('results', {}).values())
                    self.logger.info(f"✅ 주기적 수집 완료: {total_collected}개 IP")
                else:
                    self.logger.warning("⚠️ 주기적 수집 중 일부 실패")
                
                # 다음 수집까지 대기
                await asyncio.sleep(self.config['collection_interval'])
                
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
    
    async def enable_collection(self) -> Dict[str, Any]:
        """수집 시스템 활성화"""
        try:
            if self.collection_manager:
                result = self.collection_manager.enable_collection()
                self.logger.info("✅ 수집 시스템 활성화됨")
                return {'success': True, 'message': '수집 시스템이 활성화되었습니다', **result}
            else:
                self.logger.info("✅ 내장 수집 시스템 활성화됨")
                return {'success': True, 'message': '내장 수집 시스템이 활성화되었습니다'}
        except Exception as e:
            self.logger.error(f"수집 시스템 활성화 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    async def disable_collection(self) -> Dict[str, Any]:
        """수집 시스템 비활성화"""
        try:
            if self.collection_manager:
                result = self.collection_manager.disable_collection()
                self.logger.info("⏹️ 수집 시스템 비활성화됨")
                return {'success': True, 'message': '수집 시스템이 비활성화되었습니다', **result}
            else:
                self.logger.info("⏹️ 내장 수집 시스템 비활성화됨")
                return {'success': True, 'message': '내장 수집 시스템이 비활성화되었습니다'}
        except Exception as e:
            self.logger.error(f"수집 시스템 비활성화 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_collection_status(self) -> Dict[str, Any]:
        """수집 시스템 상태 조회"""
        try:
            if self.collection_manager:
                status = self.collection_manager.get_status()
            else:
                status = {
                    'enabled': True,
                    'sources': list(self._components.keys()),
                    'last_run': 'Never',
                    'mode': 'unified'
                }
            
            return {
                'success': True,
                'status': status,
                'components': {
                    'regtech_enabled': self.config['regtech_enabled'],
                    'secudium_enabled': self.config['secudium_enabled'],
                    'auto_collection': self.config['auto_collection']
                }
            }
        except Exception as e:
            self.logger.error(f"수집 상태 조회 실패: {e}")
            return {'success': False, 'error': str(e)}

# 전역 서비스 인스턴스
_unified_service = None

def get_unified_service() -> UnifiedBlacklistService:
    """통합 서비스 인스턴스 반환 (싱글톤)"""
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedBlacklistService()
    return _unified_service