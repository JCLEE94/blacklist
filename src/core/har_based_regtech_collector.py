#!/usr/bin/env python3
"""
HAR 기반 REGTECH 수집기
실제 브라우저 동작을 모방한 수집 구현
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import sqlite3
import pandas as pd
from io import BytesIO

logger = logging.getLogger(__name__)

class HarBasedRegtechCollector:
    """HAR 분석 기반 REGTECH 수집기"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.base_url = "https://regtech.fsec.or.kr"
        self.username = os.getenv('REGTECH_USERNAME', 'nextrade')
        self.password = os.getenv('REGTECH_PASSWORD', 'Sprtmxm1@3')
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
    def authenticate(self) -> bool:
        """HAR 파일에서 확인된 실제 로그인 플로우"""
        try:
            logger.info("REGTECH 로그인 시작 (HAR 기반)")
            
            # 1. 먼저 메인 페이지 방문하여 세션 초기화
            main_resp = self.session.get(f"{self.base_url}/")
            logger.info(f"메인 페이지 응답: {main_resp.status_code}")
            
            # 2. 로그인 페이지 접근
            login_page_url = f"{self.base_url}/fcti/login/loginPage"
            login_page_resp = self.session.get(login_page_url)
            logger.info(f"로그인 페이지 응답: {login_page_resp.status_code}")
            
            # 3. 로그인 요청 (HAR에서 확인된 형식)
            login_url = f"{self.base_url}/fcti/login/loginUser"
            login_data = {
                'login_error': '',
                'txId': '',
                'token': '',
                'memberId': '',
                'smsTimeExcess': 'N',
                'username': self.username,
                'password': self.password
            }
            
            login_resp = self.session.post(
                login_url,
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': self.base_url,
                    'Referer': login_page_url
                },
                allow_redirects=False
            )
            
            logger.info(f"로그인 응답 상태: {login_resp.status_code}")
            
            # 로그인 성공 여부 확인
            if login_resp.status_code == 302:
                redirect_url = login_resp.headers.get('Location', '')
                if 'error=true' in redirect_url:
                    logger.error("로그인 실패: 인증 오류")
                    return False
                logger.info("로그인 성공")
                return True
            elif login_resp.status_code == 200:
                # 응답 내용 확인
                if 'error' in login_resp.text.lower():
                    logger.error("로그인 실패: 응답에 오류 포함")
                    return False
                logger.info("로그인 성공")
                return True
            else:
                logger.error(f"예상치 않은 로그인 응답: {login_resp.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"인증 중 오류: {e}")
            return False
    
    def download_excel(self, start_date: str = None, end_date: str = None) -> Optional[str]:
        """Excel 파일 다운로드"""
        try:
            logger.info("Excel 파일 다운로드 시작")
            
            # 기본 날짜 설정 (최근 90일)
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
            
            # 다운로드 URL (HAR에서 확인)
            download_url = f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx"
            
            # 다운로드 파라미터
            params = {
                'startDate': start_date,
                'endDate': end_date,
                'blockRule': '',
                'blockTarget': ''
            }
            
            # 다운로드 요청
            response = self.session.get(
                download_url,
                params=params,
                headers={
                    'Referer': f'{self.base_url}/fcti/securityAdvisory/advisoryList'
                },
                stream=True
            )
            
            if response.status_code == 200:
                # 파일명 생성
                filename = f"fctiList_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
                file_path = self.data_dir / filename
                
                # 파일 저장
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Excel 파일 저장 완료: {file_path}")
                return str(file_path)
            else:
                logger.error(f"Excel 다운로드 실패: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Excel 다운로드 중 오류: {e}")
            return None
    
    def parse_excel_to_ips(self, file_path: str) -> List[Dict[str, Any]]:
        """Excel 파일에서 IP 추출"""
        try:
            logger.info(f"Excel 파일 파싱: {file_path}")
            
            # pandas로 Excel 읽기
            df = pd.read_excel(file_path, engine='openpyxl')
            
            # IP 주소가 있는 컬럼 찾기
            ip_columns = []
            for col in df.columns:
                if 'ip' in col.lower() or '주소' in col:
                    ip_columns.append(col)
            
            if not ip_columns:
                # 모든 컬럼에서 IP 패턴 찾기
                import re
                ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                
                ips = []
                for idx, row in df.iterrows():
                    for col in df.columns:
                        value = str(row[col])
                        matches = ip_pattern.findall(value)
                        for ip in matches:
                            if self._is_valid_ip(ip):
                                ips.append({
                                    'ip': ip,
                                    'source': 'REGTECH',
                                    'collected_at': datetime.now().isoformat()
                                })
                
                logger.info(f"Excel에서 {len(ips)}개 IP 추출")
                return ips
            
            # IP 컬럼에서 추출
            ips = []
            for col in ip_columns:
                for ip in df[col].dropna().unique():
                    ip_str = str(ip).strip()
                    if self._is_valid_ip(ip_str):
                        ips.append({
                            'ip': ip_str,
                            'source': 'REGTECH',
                            'collected_at': datetime.now().isoformat()
                        })
            
            logger.info(f"Excel에서 {len(ips)}개 IP 추출")
            return ips
            
        except Exception as e:
            logger.error(f"Excel 파싱 오류: {e}")
            return []
    
    def _is_valid_ip(self, ip: str) -> bool:
        """유효한 IP 주소인지 확인"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            # 로컬 IP나 예약된 IP 제외
            if ip.startswith(('0.', '10.', '127.', '169.254.', '172.16.', '192.168.')):
                return False
            return True
        except:
            return False
    
    def save_to_database(self, ip_data: List[Dict[str, Any]], db_path: str = None) -> bool:
        """데이터베이스에 저장 - 통합 blacklist_manager 사용"""
        try:
            logger.info(f"💾 데이터베이스 저장 시작: {len(ip_data)}개 IP")
            
            # Container에서 blacklist_manager 가져오기
            from .container import get_container
            container = get_container()
            logger.info("📦 Container 접근 성공")
            
            blacklist_manager = container.resolve('blacklist_manager')
            logger.info(f"🔧 blacklist_manager 해결: {blacklist_manager is not None}")
            
            if not blacklist_manager:
                logger.error("❌ blacklist_manager를 container에서 찾을 수 없습니다")
                logger.info("🔄 폴백 저장 방식으로 전환...")
                # 바로 폴백으로 이동
                raise Exception("blacklist_manager not available")
            
            # IP 데이터를 bulk_import_ips 형식으로 변환
            formatted_data = []
            for item in ip_data:
                formatted_entry = {
                    'ip': item['ip'],
                    'source': 'REGTECH',
                    'detection_date': datetime.now().strftime('%Y-%m-%d'),
                    'threat_type': 'blacklist',
                    'country': item.get('country', ''),
                    'confidence': 1.0
                }
                formatted_data.append(formatted_entry)
            
            logger.info(f"📝 데이터 포맷팅 완료: {len(formatted_data)}개 항목")
            
            # blacklist_manager의 bulk_import_ips 사용
            logger.info("🔧 blacklist_manager.bulk_import_ips 호출 중...")
            result = blacklist_manager.bulk_import_ips(formatted_data, source="REGTECH")
            logger.info(f"📊 bulk_import_ips 결과: {result}")
            
            if result.get('success'):
                imported_count = result.get('imported_count', 0)
                logger.info(f"✅ blacklist_manager를 통해 {imported_count}개 IP 저장 완료")
                
                # 즉시 확인
                logger.info("🔍 저장 후 즉시 확인...")
                active_ips = blacklist_manager.get_active_ips()
                logger.info(f"📈 현재 활성 IP 수: {len(active_ips) if active_ips else 0}")
                
                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ blacklist_manager 저장 실패: {error_msg}")
                logger.info("🔄 폴백 저장 방식으로 전환...")
                # 폴백으로 이동
                raise Exception(f"blacklist_manager failed: {error_msg}")
            
        except Exception as e:
            logger.error(f"❌ 통합 데이터베이스 저장 실패: {e}")
            # 폴백: 기존 방식으로 시도
            logger.info("🔄 기존 방식으로 폴백 시도...")
            try:
                if db_path:
                    db_file_path = Path(db_path)
                    logger.info(f"📂 사용자 지정 DB 경로: {db_path}")
                else:
                    db_file_path = Path("instance") / "blacklist.db"
                    logger.info(f"📂 기본 DB 경로: {db_file_path}")
                
                db_file_path.parent.mkdir(exist_ok=True)
                logger.info(f"📁 DB 디렉토리 생성 완료: {db_file_path.parent}")
                
                conn = sqlite3.connect(str(db_file_path))
                cursor = conn.cursor()
                logger.info("🗄️ SQLite 연결 성공")
                
                # 통합 스키마와 호환되는 테이블 생성
                cursor.execute('''
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
                ''')
                logger.info("🔧 테이블 생성/확인 완료")
                
                # 기존 REGTECH 데이터 확인
                cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE source = 'REGTECH'")
                existing_count = cursor.fetchone()[0]
                logger.info(f"📊 기존 REGTECH IP 수: {existing_count}")
                
                # 새 데이터 삽입 (통합 스키마 사용)
                inserted_count = 0
                for item in ip_data:
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO blacklist_ip 
                            (ip, created_at, detection_date, attack_type, country, source, confidence_score, is_active)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                        ''', (
                            item['ip'], 
                            datetime.now().isoformat(),
                            datetime.now().strftime('%Y-%m-%d'),
                            'blacklist',
                            item.get('country', ''),
                            'REGTECH',
                            1.0
                        ))
                        inserted_count += 1
                    except Exception as insert_error:
                        logger.warning(f"⚠️ IP {item['ip']} 삽입 실패: {insert_error}")
                
                conn.commit()
                logger.info("💾 커밋 완료")
                
                # 저장 후 확인
                cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE source = 'REGTECH'")
                final_count = cursor.fetchone()[0]
                logger.info(f"📈 최종 REGTECH IP 수: {final_count}")
                
                conn.close()
                
                logger.info(f"✅ 폴백으로 {inserted_count}개 IP 저장 완료 (총 {final_count}개)")
                return True
                
            except Exception as fallback_error:
                logger.error(f"❌ 폴백 저장도 실패: {fallback_error}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False
    
    def auto_collect(self, prefer_web: bool = True, db_path: str = None) -> Dict[str, Any]:
        """자동 수집 실행"""
        try:
            logger.info("REGTECH 자동 수집 시작 (HAR 기반)")
            
            # 1. 인증
            if not self.authenticate():
                return {
                    'success': False,
                    'error': '로그인 실패',
                    'method': 'har-based'
                }
            
            # 2. Excel 다운로드
            excel_file = self.download_excel()
            if not excel_file:
                return {
                    'success': False,
                    'error': 'Excel 다운로드 실패',
                    'method': 'har-based'
                }
            
            # 3. IP 추출
            ip_data = self.parse_excel_to_ips(excel_file)
            if not ip_data:
                return {
                    'success': False,
                    'error': 'IP 추출 실패',
                    'method': 'har-based'
                }
            
            # 4. 데이터베이스 저장
            db_saved = self.save_to_database(ip_data, db_path)
            
            # 5. JSON 파일로도 저장
            json_file = self.data_dir / f"regtech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'source': 'REGTECH',
                    'collected_at': datetime.now().isoformat(),
                    'total_ips': len(ip_data),
                    'ips': [item['ip'] for item in ip_data]
                }, f, ensure_ascii=False, indent=2)
            
            result = {
                'success': True,
                'method': 'har-based excel download',
                'total_collected': len(ip_data),  # 중요: collection_manager가 기대하는 키
                'saved_to_db': db_saved,
                'excel_file': excel_file,
                'json_file': str(json_file),
                'collected_at': datetime.now().isoformat()
            }
            
            logger.info(f"REGTECH 수집 완료: {len(ip_data)}개 IP")
            return result
            
        except Exception as e:
            logger.error(f"자동 수집 중 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'har-based',
                'total_collected': 0  # collection_manager가 기대하는 키
            }
        finally:
            if hasattr(self, 'session'):
                self.session.close()


# 독립 실행 지원
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    collector = HarBasedRegtechCollector()
    result = collector.auto_collect()
    
    print(json.dumps(result, indent=2, ensure_ascii=False))