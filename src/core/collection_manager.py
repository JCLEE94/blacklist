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
        
        # collection_enabled 속성 추가
        self.collection_enabled = self.config.get('collection_enabled', False)
        
        self.sources = {
            'regtech': {
                'name': 'REGTECH (금융보안원)',
                'status': 'inactive',
                'last_collection': None,
                'total_ips': 0,
                'manual_only': True,
                'enabled': self.config.get('sources', {}).get('regtech', False)
            },
            'secudium': {
                'name': 'SECUDIUM (에스케이인포섹)',
                'status': 'inactive', 
                'last_collection': None,
                'total_ips': 0,
                'manual_only': True,
                'enabled': self.config.get('sources', {}).get('secudium', False)
            }
        }
    
    def _load_collection_config(self) -> Dict[str, Any]:
        """수집 설정 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    'collection_enabled': False,
                    'sources': {'regtech': False, 'secudium': False},
                    'last_enabled_at': None,
                    'last_disabled_at': None
                }
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            return {
                'collection_enabled': False,
                'sources': {'regtech': False, 'secudium': False},
                'last_enabled_at': None,
                'last_disabled_at': None
            }
    
    def _save_collection_config(self):
        """수집 설정 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"설정 저장됨: {self.config_path}")
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
    
    def enable_collection(self, sources: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """수집 활성화 - 기존 데이터 클리어 후 신규 수집 시작"""
        try:
            # 기존 데이터 클리어
            clear_result = self.clear_all_data()
            if not clear_result.get('success', False):
                return {
                    'success': False,
                    'message': f'데이터 클리어 실패: {clear_result.get("message")}'
                }
            
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
            
            return {
                'success': True,
                'message': '수집이 활성화되었습니다. 기존 데이터가 클리어되었습니다.',
                'collection_enabled': True,
                'sources': self.config['sources'],
                'enabled_at': self.config['last_enabled_at'],
                'cleared_items': clear_result.get('cleared_items', [])
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
                'last_enabled_at': self.config.get('last_enabled_at'),
                'last_disabled_at': self.config.get('last_disabled_at'),
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
    
    def trigger_regtech_collection(self) -> Dict[str, Any]:
        """
        REGTECH 수집 트리거
        
        Returns:
            수집 결과
        """
        try:
            logger.info("REGTECH 수집 시작")
            
            # HAR 기반 REGTECH 수집기 import 및 실행
            try:
                from .har_based_regtech_collector import HarBasedRegtechCollector
                # data 디렉토리 경로 전달
                data_dir = os.path.join(os.path.dirname(self.db_path), '..', 'data')
                collector = HarBasedRegtechCollector(data_dir=data_dir)
                
                # 수집 실행 (HAR 기반 auto_collect 사용)
                result = collector.auto_collect(prefer_web=True)
                
                if result.get('success', False):
                    # 수집 성공
                    self.sources['regtech']['last_collection'] = datetime.now().isoformat()
                    self.sources['regtech']['status'] = 'active'
                    
                    # IP 수 업데이트
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
                    
            except ImportError:
                return {
                    'success': False,
                    'message': 'REGTECH 수집기 모듈을 찾을 수 없습니다',
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
        SECUDIUM 데이터 수집
        
        Returns:
            수집 결과
        """
        try:
            logger.info("SECUDIUM 수집 시작")
            
            # HAR 기반 SECUDIUM 수집기 import 및 실행 (collect_secudium_data 메서드)
            try:
                from .har_based_secudium_collector import HarBasedSecudiumCollector
                # data 디렉토리 경로 전달
                data_dir = os.path.join(os.path.dirname(self.db_path), '..', 'data')
                collector = HarBasedSecudiumCollector(data_dir=data_dir)
                
                # 수집 실행 (HAR 기반)
                result = collector.auto_collect()
                
                if result.get('success', False):
                    # 수집 성공
                    self.sources['secudium']['last_collection'] = datetime.now().isoformat()
                    self.sources['secudium']['status'] = 'active'
                    
                    # IP 수 업데이트
                    ip_count = self._get_source_ip_count('SECUDIUM')
                    self.sources['secudium']['total_ips'] = ip_count
                    
                    return {
                        'success': True,
                        'message': f'SECUDIUM 수집 완료: {ip_count:,}개 IP',
                        'source': 'secudium',
                        'timestamp': datetime.now().isoformat(),
                        'details': result
                    }
                else:
                    return {
                        'success': False,
                        'message': f'SECUDIUM 수집 실패: {result.get("message")}',
                        'source': 'secudium',
                        'timestamp': datetime.now().isoformat()
                    }
                    
            except ImportError as e:
                logger.error(f"SECUDIUM 수집기 import 실패: {e}")
                return {
                    'success': False,
                    'message': f'SECUDIUM 수집기를 찾을 수 없습니다: {e}',
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
    
    def trigger_secudium_collection(self) -> Dict[str, Any]:
        """
        SECUDIUM 수집 트리거
        
        Returns:
            수집 결과
        """
        try:
            logger.info("SECUDIUM 수집 시작")
            
            # HAR 기반 SECUDIUM 수집기 import 및 실행
            try:
                from .har_based_secudium_collector import HarBasedSecudiumCollector
                # data 디렉토리 경로 전달
                data_dir = os.path.join(os.path.dirname(self.db_path), '..', 'data')
                collector = HarBasedSecudiumCollector(data_dir=data_dir)
                
                # 수집 실행 (HAR 기반 auto_collect 사용)
                result = collector.auto_collect()
                
                if result.get('success', False):
                    # 수집 성공
                    self.sources['secudium']['last_collection'] = datetime.now().isoformat()
                    self.sources['secudium']['status'] = 'active'
                    
                    # IP 수 업데이트
                    ip_count = self._get_source_ip_count('SECUDIUM')
                    self.sources['secudium']['total_ips'] = ip_count
                    
                    return {
                        'success': True,
                        'message': f'SECUDIUM 수집 완료: {ip_count:,}개 IP',
                        'source': 'secudium',
                        'timestamp': datetime.now().isoformat(),
                        'details': result
                    }
                else:
                    return {
                        'success': False,
                        'message': f'SECUDIUM 수집 실패: {result.get("error", "Unknown error")}',
                        'source': 'secudium',
                        'timestamp': datetime.now().isoformat()
                    }
                    
            except ImportError as e:
                logger.error(f"SECUDIUM 수집기 import 실패: {e}")
                return {
                    'success': False,
                    'message': f'SECUDIUM 수집기를 찾을 수 없습니다: {e}',
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
            return count
        except Exception as e:
            logger.error(f"소스 IP 수 조회 오류: {e}")
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