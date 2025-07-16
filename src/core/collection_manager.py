"""
통합 수집 관리자 (Unified Collection Manager)
REGTECH, SECUDIUM 등 다양한 소스의 데이터 수집을 통합 관리
수집 ON/OFF 기능 및 데이터 클리어 기능 포함
"""
import os
import logging
import json
import sqlite3
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)

class CollectionManager:
    """통합 수집 관리자 - 수집 ON/OFF 및 데이터 관리"""
    
    def __init__(self, db_path: str = "instance/blacklist.db", 
                 config_path: str = "instance/collection_config.json"):
        """
        초기화
        
        Args:
            db_path: 데이터베이스 경로
            config_path: 수집 설정 파일 경로
        """
        self.db_path = db_path
        self.config_path = Path(config_path)
        
        # 설정 디렉토리 생성
        self.config_path.parent.mkdir(exist_ok=True)
        
        # 수집 설정 로드
        self.config = self._load_collection_config()
        
        # collection_enabled 속성 추가 - 기본값을 False로 설정 (수집 비활성화)
        self.collection_enabled = self.config.get('collection_enabled', False)
        
        # 일일 자동 수집 설정
        self.daily_collection_enabled = self.config.get('daily_collection_enabled', False)
        self.last_daily_collection = self.config.get('last_daily_collection', None)
        
        self.sources = {
            'regtech': {
                'name': 'REGTECH (금융보안원)',
                'status': 'inactive',
                'last_collection': None,
                'total_ips': 0,
                'manual_only': True,
                'enabled': self.config.get('sources', {}).get('regtech', False)  # 기본값 False (비활성화)
            },
            'secudium': {
                'name': 'SECUDIUM (에스케이인포섹)',
                'status': 'disabled', 
                'last_collection': None,
                'total_ips': 0,
                'manual_only': True,
                'enabled': False  # Secudium 수집기 비활성화
            }
        }
    
    def _load_collection_config(self) -> Dict[str, Any]:
        """수집 설정 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 최초 실행 확인
                    if not config.get('initial_collection_done', False):
                        logger.info("🔥 최초 실행 감지 - 수집은 기본 OFF")
                        config['collection_enabled'] = False  # 기본 OFF
                        config['sources'] = {'regtech': False, 'secudium': False}  # 모두 OFF
                        config['initial_collection_needed'] = False
                    return config
            else:
                # 설정 파일이 없으면 최초 실행
                logger.info("🔥 최초 실행 - 수집은 수동으로 활성화하세요")
                return {
                    'collection_enabled': False,  # 기본값 OFF
                    'sources': {'regtech': False, 'secudium': False},  # 모두 OFF
                    'last_enabled_at': datetime.now().isoformat(),
                    'last_disabled_at': None,
                    'daily_collection_enabled': False,
                    'last_daily_collection': None,
                    'initial_collection_done': False,  # 최초 수집 완료 플래그
                    'initial_collection_needed': True  # 최초 수집 필요
                }
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            return {
                'collection_enabled': False,  # 오류 시에도 OFF
                'sources': {'regtech': False, 'secudium': False},  # 모두 OFF
                'last_enabled_at': datetime.now().isoformat(),
                'last_disabled_at': None,
                'daily_collection_enabled': False,
                'last_daily_collection': None,
                'initial_collection_done': False,
                'initial_collection_needed': True
            }
    
    def _save_collection_config(self):
        """수집 설정 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"설정 저장됨: {self.config_path}")
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
    
    def enable_collection(self, sources: Optional[Dict[str, bool]] = None, clear_data: bool = False) -> Dict[str, Any]:
        """수집 활성화 - 선택적으로 기존 데이터 클리어"""
        try:
            # 이미 활성화되어 있는지 확인
            was_already_enabled = self.config.get('collection_enabled', False)
            cleared_data = False
            clear_result = {'cleared_items': []}
            
            # 명시적으로 요청된 경우에만 데이터 클리어
            if clear_data:
                clear_result = self.clear_all_data()
                if not clear_result.get('success', False):
                    return {
                        'success': False,
                        'message': f'데이터 클리어 실패: {clear_result.get("message")}'
                    }
                cleared_data = True
            
            # 수집 활성화
            self.config['collection_enabled'] = True
            self.collection_enabled = True  # 인스턴스 속성도 업데이트
            self.config['last_enabled_at'] = datetime.now().isoformat()
            
            if sources:
                self.config['sources'].update(sources)
            else:
                # 기본적으로 모든 소스 활성화
                for source in self.config['sources']:
                    self.config['sources'][source] = True
            
            # 소스 상태 업데이트
            for source_key in self.sources:
                self.sources[source_key]['enabled'] = self.config['sources'].get(source_key, False)
            
            self._save_collection_config()
            
            logger.info("수집이 활성화되었습니다. 모든 기존 데이터가 삭제되었습니다.")
            
            message = '수집이 활성화되었습니다.'
            if cleared_data:
                message += ' 기존 데이터가 클리어되었습니다.'
            elif was_already_enabled:
                message = '수집은 이미 활성화 상태입니다.'
            
            return {
                'success': True,
                'message': message,
                'collection_enabled': True,
                'cleared_data': cleared_data,
                'sources': self.config['sources'],
                'enabled_at': self.config['last_enabled_at'],
                'cleared_items': clear_result.get('cleared_items', []) if cleared_data else []
            }
            
        except Exception as e:
            logger.error(f"수집 활성화 실패: {e}")
            return {
                'success': False,
                'message': f'수집 활성화 실패: {str(e)}'
            }
    
    def disable_collection(self) -> Dict[str, Any]:
        """수집 비활성화"""
        try:
            self.config['collection_enabled'] = False
            self.collection_enabled = False  # 인스턴스 속성도 업데이트
            self.config['last_disabled_at'] = datetime.now().isoformat()
            
            # 모든 소스 비활성화
            for source in self.config['sources']:
                self.config['sources'][source] = False
            
            # 소스 상태 업데이트
            for source_key in self.sources:
                self.sources[source_key]['enabled'] = False
            
            self._save_collection_config()
            
            logger.info("수집이 비활성화되었습니다.")
            
            return {
                'success': True,
                'message': '수집이 비활성화되었습니다.',
                'collection_enabled': False,
                'disabled_at': self.config['last_disabled_at']
            }
            
        except Exception as e:
            logger.error(f"수집 비활성화 실패: {e}")
            return {
                'success': False,
                'message': f'수집 비활성화 실패: {str(e)}'
            }
    
    def clear_all_data(self) -> Dict[str, Any]:
        """모든 데이터 클리어"""
        try:
            cleared_items = []
            
            # 1. 데이터베이스 클리어
            if Path(self.db_path).exists():
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 테이블별 데이터 삭제
                tables = ['blacklist_ip', 'ip_detection', 'daily_stats']
                for table in tables:
                    try:
                        cursor.execute(f"DELETE FROM {table}")
                        row_count = cursor.rowcount
                        cleared_items.append(f"테이블 {table}: {row_count}개 레코드 삭제")
                    except sqlite3.Error as e:
                        logger.warning(f"테이블 {table} 삭제 중 오류: {e}")
                
                conn.commit()
                conn.close()
                logger.info("데이터베이스 클리어 완료")
            
            # 2. 데이터 디렉토리 클리어
            data_dirs = [
                'data/blacklist',
                'data/sources',
                'data/regtech',
                'data/secudium'
            ]
            
            for data_dir in data_dirs:
                dir_path = Path(data_dir)
                if dir_path.exists():
                    try:
                        shutil.rmtree(dir_path)
                        dir_path.mkdir(parents=True, exist_ok=True)
                        cleared_items.append(f"디렉토리 {data_dir} 클리어")
                    except Exception as e:
                        logger.warning(f"디렉토리 {data_dir} 클리어 실패: {e}")
            
            # 3. 캐시 파일 클리어
            cache_files = [
                'instance/.cache_stats',
                'instance/.last_update'
            ]
            
            for cache_file in cache_files:
                cache_path = Path(cache_file)
                if cache_path.exists():
                    try:
                        cache_path.unlink()
                        cleared_items.append(f"캐시 파일 {cache_file} 삭제")
                    except Exception as e:
                        logger.warning(f"캐시 파일 {cache_file} 삭제 실패: {e}")
            
            # 소스 상태 초기화
            for source_key in self.sources:
                self.sources[source_key]['total_ips'] = 0
                self.sources[source_key]['status'] = 'inactive'
                self.sources[source_key]['last_collection'] = None
            
            logger.info(f"데이터 클리어 완료: {len(cleared_items)}개 항목")
            
            return {
                'success': True,
                'message': '모든 데이터가 클리어되었습니다.',
                'cleared_items': cleared_items,
                'cleared_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"데이터 클리어 실패: {e}")
            return {
                'success': False,
                'message': f'데이터 클리어 실패: {str(e)}'
            }
    
    def is_collection_enabled(self, source: Optional[str] = None) -> bool:
        """수집 활성화 상태 확인"""
        if not self.config.get('collection_enabled', False):
            return False
        
        if source:
            return self.config.get('sources', {}).get(source, False)
        
        return True
        
    def get_status(self) -> Dict[str, Any]:
        """
        수집 서비스 전체 상태 반환 (ON/OFF 상태 포함)
        
        Returns:
            수집 상태 정보
        """
        try:
            # 데이터베이스에서 실제 IP 수 확인
            total_ips = self._get_total_ip_count()
            
            # 각 소스별 IP 수 확인
            for source_key in self.sources.keys():
                self.sources[source_key]['total_ips'] = self._get_source_ip_count(source_key.upper())
            
            active_sources = sum(1 for s in self.sources.values() if s['total_ips'] > 0)
            enabled_sources = sum(1 for s in self.sources.values() if s.get('enabled', False))
            
            return {
                'status': 'active' if self.config.get('collection_enabled', False) else 'inactive',
                'collection_enabled': self.config.get('collection_enabled', False),
                'daily_collection_enabled': self.daily_collection_enabled,
                'last_enabled_at': self.config.get('last_enabled_at'),
                'last_disabled_at': self.config.get('last_disabled_at'),
                'last_daily_collection': self.last_daily_collection,
                'last_updated': datetime.now().isoformat(),
                'sources': {
                    source_key: {
                        'name': source_info['name'],
                        'enabled': source_info.get('enabled', False),
                        'status': 'active' if source_info['total_ips'] > 0 else 'no_data',
                        'last_collection': source_info['last_collection'],
                        'total_ips': source_info['total_ips'],
                        'manual_only': source_info.get('manual_only', False)
                    }
                    for source_key, source_info in self.sources.items()
                },
                'summary': {
                    'total_sources': len(self.sources),
                    'enabled_sources': enabled_sources,
                    'active_sources': active_sources,
                    'total_ips_collected': total_ips
                }
            }
        except Exception as e:
            logger.error(f"상태 조회 오류: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }
    
    def set_daily_collection_enabled(self) -> Dict[str, Any]:
        """
        일일 자동 수집 활성화
        """
        try:
            self.daily_collection_enabled = True
            self.config['daily_collection_enabled'] = True
            self._save_collection_config()
            
            logger.info("✅ 일일 자동 수집 활성화")
            
            return {
                'success': True,
                'message': '일일 자동 수집이 활성화되었습니다',
                'daily_collection_enabled': True
            }
        except Exception as e:
            logger.error(f"일일 자동 수집 활성화 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def set_daily_collection_disabled(self) -> Dict[str, Any]:
        """
        일일 자동 수집 비활성화
        """
        try:
            self.daily_collection_enabled = False
            self.config['daily_collection_enabled'] = False
            self._save_collection_config()
            
            logger.info("⏹️ 일일 자동 수집 비활성화")
            
            return {
                'success': True,
                'message': '일일 자동 수집이 비활성화되었습니다',
                'daily_collection_enabled': False
            }
        except Exception as e:
            logger.error(f"일일 자동 수집 비활성화 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def trigger_daily_collection(self) -> Dict[str, Any]:
        """
        일일 자동 수집 실행 (하루 단위 데이터만)
        """
        try:
            if not self.daily_collection_enabled:
                return {
                    'success': False,
                    'message': '일일 자동 수집이 비활성화 상태입니다'
                }
            
            # 오늘 날짜로 수집 범위 설정
            today = datetime.now()
            start_date = today.strftime('%Y%m%d')
            end_date = today.strftime('%Y%m%d')
            
            logger.info(f"🔄 일일 자동 수집 시작: {start_date}")
            
            results = {}
            
            # REGTECH 수집 (하루 단위)
            regtech_result = self.trigger_regtech_collection(start_date=start_date, end_date=end_date)
            results['regtech'] = regtech_result
            
            # SECUDIUM 수집 (하루 단위)
            secudium_result = self.trigger_secudium_collection()
            results['secudium'] = secudium_result
            
            # 마지막 수집 시간 업데이트
            self.last_daily_collection = datetime.now().isoformat()
            self.config['last_daily_collection'] = self.last_daily_collection
            self._save_collection_config()
            
            return {
                'success': True,
                'message': '일일 자동 수집 완료',
                'collection_date': start_date,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"일일 자동 수집 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def mark_initial_collection_done(self):
        """최초 수집 완료 표시"""
        self.config['initial_collection_done'] = True
        self.config['initial_collection_needed'] = False
        self._save_collection_config()
        logger.info("✅ 최초 수집 완료 표시")
    
    def is_initial_collection_needed(self) -> bool:
        """최초 수집이 필요한지 확인"""
        return self.config.get('initial_collection_needed', False)
    
    def trigger_regtech_collection(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        REGTECH 수집 트리거
        
        Args:
            start_date: 시작일 (YYYYMMDD), None이면 최근 90일
            end_date: 종료일 (YYYYMMDD), None이면 오늘
            
        Returns:
            수집 결과
        """
        try:
            logger.info(f"REGTECH 수집 시작 (start_date={start_date}, end_date={end_date})")
            
            # Enhanced REGTECH 수집기 import 및 실행
            try:
                # Enhanced 수집기 우선 시도
                try:
                    from .regtech_collector_enhanced import EnhancedRegtechCollector
                    data_dir = os.path.join(os.path.dirname(self.db_path), '..', 'data')
                    collector = EnhancedRegtechCollector(data_dir=data_dir)
                    
                    # 수집 실행
                    logger.info(f"Enhanced REGTECH 수집기 사용 (start_date={start_date}, end_date={end_date})")
                    ips = collector.collect_from_web(start_date=start_date, end_date=end_date)
                    
                    if ips:
                        # 데이터베이스에 저장
                        saved_count = self._save_ips_to_database(ips, 'REGTECH')
                        
                        # 수집 성공
                        self.sources['regtech']['last_collection'] = datetime.now().isoformat()
                        self.sources['regtech']['status'] = 'active'
                        
                        # IP 수 업데이트
                        ip_count = self._get_source_ip_count('REGTECH')
                        self.sources['regtech']['total_ips'] = ip_count
                        
                        return {
                            'success': True,
                            'message': f'REGTECH 수집 완료: {saved_count:,}개 IP 저장 (총 {ip_count:,}개)',
                            'source': 'regtech',
                            'timestamp': datetime.now().isoformat(),
                            'details': {
                                'collected': len(ips),
                                'saved': saved_count,
                                'total_in_db': ip_count,
                                'collector': 'enhanced'
                            }
                        }
                    else:
                        return {
                            'success': False,
                            'message': 'REGTECH 수집 실패: 데이터를 가져오지 못했습니다',
                            'source': 'regtech',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                except ImportError:
                    # HAR 기반 수집기로 폴백
                    logger.warning("Enhanced 수집기 사용 불가, HAR 기반 수집기로 폴백")
                    from .har_based_regtech_collector import HarBasedRegtechCollector
                    data_dir = os.path.join(os.path.dirname(self.db_path), '..', 'data')
                    collector = HarBasedRegtechCollector(data_dir=data_dir)
                    
                    if start_date and end_date:
                        ips = collector.collect_from_web(start_date=start_date, end_date=end_date)
                        result = {
                            'success': True if ips else False,
                            'total_collected': len(ips) if ips else 0,
                            'ips': ips
                        }
                    else:
                        result = collector.auto_collect(prefer_web=True, db_path=self.db_path)
                    
                    if result.get('success', False):
                        self.sources['regtech']['last_collection'] = datetime.now().isoformat()
                        self.sources['regtech']['status'] = 'active'
                        ip_count = self._get_source_ip_count('REGTECH')
                        self.sources['regtech']['total_ips'] = ip_count
                        
                        return {
                            'success': True,
                            'message': f'REGTECH 수집 완료: {ip_count:,}개 IP',
                            'source': 'regtech',
                            'timestamp': datetime.now().isoformat(),
                            'details': result
                        }
                    else:
                        return {
                            'success': False,
                            'message': f'REGTECH 수집 실패: {result.get("error", "알 수 없는 오류")}',
                            'source': 'regtech',
                            'timestamp': datetime.now().isoformat()
                        }
                    
            except ImportError as e:
                logger.error(f"REGTECH 수집기 import 실패: {e}")
                return {
                    'success': False,
                    'message': f'REGTECH 수집기 모듈을 찾을 수 없습니다: {e}',
                    'source': 'regtech',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"REGTECH 수집 오류: {e}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'REGTECH 수집 중 오류 발생: {str(e)}',
                'source': 'regtech',
                'timestamp': datetime.now().isoformat()
            }
    
    def collect_secudium_data(self) -> Dict[str, Any]:
        """
        SECUDIUM 데이터 수집 (trigger_secudium_collection과 동일)
        
        Returns:
            수집 결과
        """
        return self.trigger_secudium_collection()
    
    def trigger_secudium_collection(self) -> Dict[str, Any]:
        """
        SECUDIUM 수집 트리거
        
        Returns:
            수집 결과
        """
        try:
            logger.info("SECUDIUM 수집 시작")
            
            # HAR 기반 SECUDIUM 수집기 우선 시도
            try:
                logger.info("HAR 기반 SECUDIUM 수집기 import 시도")
                from .har_based_secudium_collector import HarBasedSecudiumCollector
                logger.info("HAR 기반 SECUDIUM 수집기 import 성공")
                
                # data 디렉토리 경로 전달
                data_dir = os.path.join(os.path.dirname(self.db_path), '..', 'data')
                collector = HarBasedSecudiumCollector(data_dir=data_dir)
                logger.info(f"HAR 기반 SECUDIUM 수집기 인스턴스 생성 완료 (data_dir: {data_dir})")
                
                # 수집 실행 (HAR 기반 auto_collect 사용)
                logger.info("HAR 기반 SECUDIUM 수집기 사용하여 auto_collect 시작")
                result = collector.auto_collect(db_path=self.db_path)
                logger.info(f"HAR 기반 SECUDIUM 수집기 결과: {result}")
                
                if result.get('success', False):
                    # 수집 성공
                    self.sources['secudium']['last_collection'] = datetime.now().isoformat()
                    self.sources['secudium']['status'] = 'active'
                    
                    # IP 수 업데이트
                    ip_count = self._get_source_ip_count('SECUDIUM')
                    self.sources['secudium']['total_ips'] = ip_count
                    
                    return {
                        'success': True,
                        'message': f'SECUDIUM 수집 완료: {ip_count:,}개 IP (HAR 기반)',
                        'source': 'secudium',
                        'timestamp': datetime.now().isoformat(),
                        'details': result
                    }
                else:
                    # HAR 기반 수집기 실패 시 일반 수집기로 폴백
                    logger.warning("HAR 기반 수집기 실패, 일반 수집기로 폴백")
                    from .secudium_collector import SecudiumCollector
                    collector = SecudiumCollector(data_dir=data_dir)
                    
                    # 웹 수집 시도
                    collected_data = collector.collect_from_web()
                    
                    if collected_data:
                        # 데이터베이스에 저장
                        saved_count = self._save_ips_to_database(collected_data, 'SECUDIUM')
                        
                        # 수집 성공
                        self.sources['secudium']['last_collection'] = datetime.now().isoformat()
                        self.sources['secudium']['status'] = 'active'
                        
                        # IP 수 업데이트
                        ip_count = self._get_source_ip_count('SECUDIUM')
                        self.sources['secudium']['total_ips'] = ip_count
                        
                        return {
                            'success': True,
                            'message': f'SECUDIUM 수집 완료: {saved_count:,}개 IP 저장 (총 {ip_count:,}개)',
                            'source': 'secudium',
                            'timestamp': datetime.now().isoformat(),
                            'details': {
                                'collected': len(collected_data),
                                'saved': saved_count,
                                'total_in_db': ip_count,
                                'collector': 'standard'
                            }
                        }
                    else:
                        return {
                            'success': False,
                            'message': 'SECUDIUM 수집 실패: 모든 방법으로 데이터를 가져오지 못했습니다',
                            'source': 'secudium',
                            'timestamp': datetime.now().isoformat()
                        }
                    
            except ImportError as e:
                # 일반 수집기만 시도
                logger.error(f"HAR 기반 수집기 import 실패: {e}")
                import traceback
                logger.error(f"Import 실패 상세: {traceback.format_exc()}")
                logger.warning("일반 수집기로 폴백")
                from .secudium_collector import SecudiumCollector
                data_dir = os.path.join(os.path.dirname(self.db_path), '..', 'data')
                collector = SecudiumCollector(data_dir=data_dir)
                logger.info(f"일반 SECUDIUM 수집기 인스턴스 생성 완료 (data_dir: {data_dir})")
                
                # 웹 수집 시도
                collected_data = collector.collect_from_web()
                
                if collected_data:
                    # 데이터베이스에 저장
                    saved_count = self._save_ips_to_database(collected_data, 'SECUDIUM')
                    
                    # 수집 성공
                    self.sources['secudium']['last_collection'] = datetime.now().isoformat()
                    self.sources['secudium']['status'] = 'active'
                    
                    # IP 수 업데이트
                    ip_count = self._get_source_ip_count('SECUDIUM')
                    self.sources['secudium']['total_ips'] = ip_count
                    
                    return {
                        'success': True,
                        'message': f'SECUDIUM 수집 완료: {saved_count:,}개 IP 저장 (총 {ip_count:,}개)',
                        'source': 'secudium',
                        'timestamp': datetime.now().isoformat(),
                        'details': {
                            'collected': len(collected_data),
                            'saved': saved_count,
                            'total_in_db': ip_count,
                            'collector': 'standard'
                        }
                    }
                else:
                    return {
                        'success': False,
                        'message': 'SECUDIUM 수집 실패: 데이터를 가져오지 못했습니다',
                        'source': 'secudium',
                        'timestamp': datetime.now().isoformat()
                    }
                
        except Exception as e:
            logger.error(f"SECUDIUM 수집 오류: {e}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'SECUDIUM 수집 중 오류 발생: {str(e)}',
                'source': 'secudium',
                'timestamp': datetime.now().isoformat()
            }
    
    def get_collection_history(self, source: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        수집 히스토리 조회
        
        Args:
            source: 특정 소스 (없으면 전체)
            limit: 최대 결과 수
            
        Returns:
            수집 히스토리 목록
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if source:
                cursor.execute("""
                    SELECT ip, source, detection_date, created_at 
                    FROM blacklist_ip 
                    WHERE UPPER(source) = UPPER(?)
                    ORDER BY created_at DESC LIMIT ?
                """, (source, limit))
            else:
                cursor.execute("""
                    SELECT ip, source, detection_date, created_at 
                    FROM blacklist_ip 
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'ip': row[0],
                    'source': row[1],
                    'detection_date': row[2],
                    'created_at': row[3]
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"수집 히스토리 조회 오류: {e}")
            return []
    
    def _get_total_ip_count(self) -> int:
        """총 IP 수 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"총 IP 수 조회 오류: {e}")
            return 0
    
    def _get_source_ip_count(self, source: str) -> int:
        """특정 소스의 IP 수 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM blacklist_ip WHERE UPPER(source) = UPPER(?)",
                (source,)
            )
            count = cursor.fetchone()[0]
            conn.close()
            logger.debug(f"Source {source} has {count} IPs in database")
            return count
        except Exception as e:
            logger.error(f"소스 IP 수 조회 오류: {e}")
            return 0
    
    def _save_ips_to_database(self, ips: List[Any], source: str) -> int:
        """
        IP 목록을 데이터베이스에 저장
        
        Args:
            ips: BlacklistEntry 객체 목록
            source: 소스명
            
        Returns:
            저장된 IP 수
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            saved_count = 0
            
            for ip_entry in ips:
                try:
                    # BlacklistEntry 객체에서 데이터 추출
                    ip_address = ip_entry.ip_address
                    country = getattr(ip_entry, 'country', 'Unknown')
                    reason = getattr(ip_entry, 'reason', '')
                    reg_date = getattr(ip_entry, 'reg_date', datetime.now().strftime('%Y-%m-%d'))
                    threat_level = getattr(ip_entry, 'threat_level', 'high')
                    
                    # 중복 확인
                    cursor.execute(
                        "SELECT COUNT(*) FROM blacklist_ip WHERE ip = ? AND source = ?",
                        (ip_address, source)
                    )
                    
                    if cursor.fetchone()[0] == 0:
                        # 새로운 IP 삽입
                        cursor.execute("""
                            INSERT INTO blacklist_ip 
                            (ip, source, country, reason, detection_date, threat_level, is_active, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))
                        """, (ip_address, source, country, reason, reg_date, threat_level))
                        saved_count += 1
                    else:
                        # 기존 IP 업데이트
                        cursor.execute("""
                            UPDATE blacklist_ip 
                            SET country = ?, reason = ?, detection_date = ?, 
                                threat_level = ?, updated_at = datetime('now')
                            WHERE ip = ? AND source = ?
                        """, (country, reason, reg_date, threat_level, ip_address, source))
                        
                except Exception as e:
                    logger.warning(f"IP 저장 중 오류 ({ip_address}): {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            logger.info(f"{source}: {saved_count}개 IP 저장됨")
            return saved_count
            
        except Exception as e:
            logger.error(f"데이터베이스 저장 오류: {e}")
            return 0
    
    def clear_source_data(self, source: str) -> Dict[str, Any]:
        """
        특정 소스의 데이터 삭제
        
        Args:
            source: 삭제할 소스명
            
        Returns:
            삭제 결과
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM blacklist_ip WHERE UPPER(source) = UPPER(?)",
                (source,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            # 소스 상태 업데이트
            source_key = source.lower()
            if source_key in self.sources:
                self.sources[source_key]['total_ips'] = 0
                self.sources[source_key]['status'] = 'inactive'
            
            return {
                'success': True,
                'message': f'{source} 데이터 삭제 완료: {deleted_count:,}개',
                'deleted_count': deleted_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"소스 데이터 삭제 오류: {e}")
            return {
                'success': False,
                'message': f'{source} 데이터 삭제 실패: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

# 전역 인스턴스
collection_manager = CollectionManager()