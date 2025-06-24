#!/usr/bin/env python3
"""
HAR 분석 기반 실제 API 요청 구현
REGTECH와 SECUDIUM의 실제 API 엔드포인트로 직접 요청
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
from io import BytesIO
import sqlite3
import time

class HARBasedCollector:
    """HAR 파일 분석 결과를 기반으로 한 실제 API 수집기"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
    def collect_regtech_direct(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        REGTECH Excel 다운로드 - HAR 분석 기반 직접 요청
        URL: https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryListDownloadXlsx
        """
        print("🔍 REGTECH 직접 수집 시작...")
        
        # 기본 날짜 설정 (최근 3개월)
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
        
        # 먼저 로그인 페이지 방문으로 세션 설정
        login_page = "https://regtech.fsec.or.kr/"
        self.session.get(login_page)
        
        url = "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryListDownloadXlsx"
        
        # HAR에서 추출한 정확한 파라미터
        form_data = {
            'page': '0',
            'tabSort': 'blacklist',
            'excelDownload': 'security,blacklist,weakpoint,',
            'cveId': '',
            'ipId': '',
            'estId': '',
            'startDate': start_date,
            'endDate': end_date,
            'findCondition': 'all',
            'findKeyword': '',
            'excelDown': ['security', 'blacklist', 'weakpoint'],
            'size': '1000'  # 더 많은 데이터 요청
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://regtech.fsec.or.kr',
            'Referer': 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            print(f"   📅 수집 기간: {start_date} ~ {end_date}")
            print(f"   🌐 요청 URL: {url}")
            
            response = self.session.post(url, data=form_data, headers=headers, timeout=30)
            
            print(f"   📊 응답 상태: {response.status_code}")
            print(f"   📊 응답 헤더: {dict(response.headers)}")
            
            if response.status_code == 200:
                # Content-Disposition 확인
                content_disp = response.headers.get('Content-Disposition', '')
                if 'attachment' in content_disp and 'xlsx' in content_disp:
                    print(f"   ✅ Excel 파일 수신 성공: {content_disp}")
                    
                    # Excel 파일 파싱
                    excel_data = self._parse_regtech_excel(response.content)
                    return {
                        'success': True,
                        'source': 'REGTECH',
                        'method': 'direct_api_excel',
                        'period': f"{start_date}~{end_date}",
                        'data': excel_data,
                        'total_ips': len(excel_data)
                    }
                else:
                    print(f"   ⚠️ 예상과 다른 응답: {response.text[:500]}")
                    return {
                        'success': False,
                        'error': 'Not Excel file response',
                        'response_preview': response.text[:500]
                    }
            else:
                print(f"   ❌ 요청 실패: {response.status_code}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'response': response.text[:500]
                }
                
        except Exception as e:
            print(f"   ❌ REGTECH 수집 오류: {e}")
            return {'success': False, 'error': str(e)}
    
    def collect_secudium_direct(self) -> Dict[str, Any]:
        """
        SECUDIUM 로그인 및 데이터 수집 - HAR 분석 기반
        """
        print("🔍 SECUDIUM 직접 수집 시작...")
        
        # 1단계: 로그인
        login_result = self._secudium_login()
        if not login_result['success']:
            return login_result
        
        # 2단계: 블랙리스트 데이터 요청
        return self._secudium_get_blacklist()
    
    def _secudium_login(self) -> Dict[str, Any]:
        """SECUDIUM 로그인 처리"""
        print("   🔐 SECUDIUM 로그인 중...")
        
        # 기존 세션 끊기 요청 먼저 시도
        logout_url = "https://secudium.skinfosec.co.kr/isap-api/logout"
        try:
            self.session.post(logout_url, timeout=10)
            print("   🔄 기존 세션 로그아웃 시도")
        except:
            pass
        
        login_url = "https://secudium.skinfosec.co.kr/isap-api/loginProcess"
        
        # HAR에서 추출한 정확한 로그인 데이터
        login_data = {
            'lang': 'ko',
            'is_otp': 'N',
            'is_expire': 'N',
            'login_name': 'nextrade',
            'password': 'Sprtmxm1@3',
            'otp_value': ''
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://secudium.skinfosec.co.kr',
            'Referer': 'https://secudium.skinfosec.co.kr/login',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }
        
        try:
            response = self.session.post(login_url, data=login_data, headers=headers, timeout=15)
            
            print(f"   📊 로그인 응답: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"   📊 로그인 결과: {result}")
                    
                    # 응답 구조 분석
                    response_data = result.get('response', {})
                    
                    # already.login 오류 처리 - 기존 접속 끊고 재로그인 시도
                    if response_data.get('code') == 'already.login':
                        print("   🔄 이미 로그인된 상태 - 기존 세션 끊고 재시도")
                        
                        # 강제 로그아웃 후 재로그인
                        force_login_data = login_data.copy()
                        force_login_data['force_login'] = 'Y'  # 강제 로그인 플래그
                        
                        response = self.session.post(login_url, data=force_login_data, headers=headers, timeout=15)
                        if response.status_code == 200:
                            try:
                                result = response.json()
                                response_data = result.get('response', {})
                            except:
                                pass
                    
                    # 성공 체크
                    if response_data.get('error') == False and 'token' in response_data:
                        print("   ✅ 로그인 성공 - 토큰 획득")
                        token = response_data['token']
                        self.session.headers.update({
                            'X-Auth-Token': token,
                            'Authorization': f'Bearer {token}'
                        })
                        return {'success': True, 'session': self.session, 'token': token}
                    elif result.get('result') == 'success' or 'success' in str(result).lower():
                        print("   ✅ 로그인 성공")
                        return {'success': True, 'session': self.session}
                    else:
                        print(f"   ❌ 로그인 실패: {result}")
                        return {'success': False, 'error': result}
                        
                except json.JSONDecodeError:
                    print(f"   ⚠️ JSON 파싱 실패, 원본: {response.text[:200]}")
                    # 응답에 success가 포함되어 있으면 성공으로 간주
                    if 'success' in response.text.lower() or response.status_code == 200:
                        print("   ✅ 로그인 성공 (추정)")
                        return {'success': True, 'session': self.session}
                    return {'success': False, 'error': 'Login response parsing failed'}
            else:
                print(f"   ❌ 로그인 HTTP 오류: {response.status_code}")
                return {'success': False, 'error': f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"   ❌ 로그인 예외: {e}")
            return {'success': False, 'error': str(e)}
    
    def _secudium_get_blacklist(self) -> Dict[str, Any]:
        """SECUDIUM 블랙리스트 데이터 요청"""
        print("   📋 SECUDIUM 블랙리스트 요청 중...")
        
        # 블랙리스트 API 엔드포인트 (HAR 분석 결과 기반)
        blacklist_url = "https://secudium.skinfosec.co.kr/isap-api/secinfo/list/black_ip"
        
        # 일반적인 페이징 파라미터로 시도
        params = {
            'page': '0',
            'size': '1000',
            'sort': 'regDate,desc'
        }
        
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://secudium.skinfosec.co.kr/secinfo/black_ip'
        }
        
        try:
            response = self.session.get(blacklist_url, params=params, headers=headers, timeout=15)
            
            print(f"   📊 블랙리스트 응답: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 데이터 구조: {type(data)}")
                    
                    if isinstance(data, dict):
                        rows = data.get('rows', [])
                        if rows:
                            parsed_data = self._parse_secudium_data(rows)
                            return {
                                'success': True,
                                'source': 'SECUDIUM',
                                'method': 'direct_api_json',
                                'data': parsed_data,
                                'total_entries': len(rows)
                            }
                    
                    print(f"   ⚠️ 예상과 다른 데이터 구조: {str(data)[:200]}")
                    return {'success': False, 'error': 'Unexpected data structure'}
                    
                except json.JSONDecodeError:
                    print(f"   ⚠️ JSON 파싱 실패: {response.text[:200]}")
                    return {'success': False, 'error': 'JSON parsing failed'}
            else:
                print(f"   ❌ 블랙리스트 요청 실패: {response.status_code}")
                print(f"   📊 응답 내용: {response.text[:300]}")
                return {'success': False, 'error': f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"   ❌ 블랙리스트 요청 예외: {e}")
            return {'success': False, 'error': str(e)}
    
    def _parse_regtech_excel(self, excel_content: bytes) -> List[Dict[str, Any]]:
        """REGTECH Excel 파일 파싱"""
        try:
            df = pd.read_excel(BytesIO(excel_content))
            print(f"   📊 Excel 컬럼: {list(df.columns)}")
            print(f"   📊 Excel 행 수: {len(df)}")
            
            parsed_data = []
            for _, row in df.iterrows():
                # 컬럼명에 따라 적절히 매핑
                ip_col = None
                for col in df.columns:
                    if 'ip' in col.lower() or 'IP' in col or '아이피' in col:
                        ip_col = col
                        break
                
                if ip_col and not pd.isna(row[ip_col]):
                    parsed_data.append({
                        'ip': str(row[ip_col]).strip(),
                        'source': 'REGTECH',
                        'detection_date': datetime.now().strftime('%Y-%m-%d'),
                        'attack_type': 'Excel Import',
                        'country': 'Unknown',
                        'collection_method': 'direct_excel_api'
                    })
            
            return parsed_data
            
        except Exception as e:
            print(f"   ⚠️ Excel 파싱 오류: {e}")
            return []
    
    def _parse_secudium_data(self, rows: List[Dict]) -> List[Dict[str, Any]]:
        """SECUDIUM JSON 데이터 파싱"""
        parsed_data = []
        
        for row in rows:
            # rows 데이터 구조 분석
            row_data = row.get('data', [])
            if isinstance(row_data, list) and len(row_data) > 0:
                # IP 정보 추출 시도
                for item in row_data:
                    if isinstance(item, str) and self._is_valid_ip(item):
                        parsed_data.append({
                            'ip': item,
                            'source': 'SECUDIUM', 
                            'detection_date': datetime.now().strftime('%Y-%m-%d'),
                            'attack_type': 'SK쉴더스 탐지',
                            'country': 'Unknown',
                            'collection_method': 'direct_json_api'
                        })
                        break
        
        return parsed_data
    
    def _is_valid_ip(self, ip: str) -> bool:
        """IP 주소 유효성 검증"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            return True
        except:
            return False
    
    def save_to_database(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """데이터베이스에 저장"""
        print("💾 데이터베이스에 저장 중...")
        
        try:
            conn = sqlite3.connect('instance/blacklist.db')
            cursor = conn.cursor()
            
            inserted = 0
            for item in data:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO blacklist_ip 
                        (ip, country, attack_type, source, detection_date, source_detail, collection_method)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('ip', ''),
                        item.get('country', 'Unknown'),
                        item.get('attack_type', 'Unknown'),
                        item.get('source', 'Unknown'),
                        item.get('detection_date', datetime.now().strftime('%Y-%m-%d')),
                        item.get('source_detail', 'HAR API Direct'),
                        item.get('collection_method', 'har_api_direct')
                    ))
                    
                    if cursor.rowcount > 0:
                        inserted += 1
                        
                except Exception as e:
                    print(f"   ⚠️ 데이터 삽입 오류: {e}")
                    continue
            
            conn.commit()
            
            # 전체 통계
            total_count = cursor.execute('SELECT COUNT(*) FROM blacklist_ip').fetchone()[0]
            conn.close()
            
            print(f"   ✅ 저장 완료: {inserted}개 신규 IP")
            print(f"   📊 전체 DB: {total_count}개 IP")
            
            return {
                'success': True,
                'inserted': inserted,
                'total_count': total_count
            }
            
        except Exception as e:
            print(f"   ❌ 데이터베이스 저장 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_complete_collection(self) -> Dict[str, Any]:
        """완전한 HAR 기반 수집 실행"""
        print("🚀 HAR 기반 실제 API 수집 시작")
        print("=" * 60)
        
        all_data = []
        results = {}
        
        # 1. REGTECH 직접 수집
        regtech_result = self.collect_regtech_direct()
        results['regtech'] = regtech_result
        
        if regtech_result['success']:
            all_data.extend(regtech_result['data'])
            print(f"   ✅ REGTECH: {len(regtech_result['data'])}개 IP 수집")
        else:
            print(f"   ❌ REGTECH 실패: {regtech_result.get('error', 'Unknown')}")
        
        time.sleep(2)  # 요청 간격
        
        # 2. SECUDIUM 직접 수집
        secudium_result = self.collect_secudium_direct()
        results['secudium'] = secudium_result
        
        if secudium_result['success']:
            all_data.extend(secudium_result['data'])
            print(f"   ✅ SECUDIUM: {len(secudium_result['data'])}개 IP 수집")
        else:
            print(f"   ❌ SECUDIUM 실패: {secudium_result.get('error', 'Unknown')}")
        
        # 3. 데이터베이스 저장
        if all_data:
            db_result = self.save_to_database(all_data)
            results['database'] = db_result
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 HAR 기반 실제 수집 결과")
        print("=" * 60)
        print(f"📊 총 수집: {len(all_data)}개 IP")
        
        if 'database' in results:
            db_stats = results['database']
            if db_stats.get('success'):
                print(f"💾 DB 저장: {db_stats['inserted']}개 신규 추가")
                print(f"📊 전체 DB: {db_stats['total_count']}개 IP")
        
        return {
            'success': len(all_data) > 0,
            'total_collected': len(all_data),
            'results': results
        }

def main():
    """메인 실행"""
    collector = HARBasedCollector()
    
    result = collector.run_complete_collection()
    
    if result['success']:
        print(f"\n🎉 HAR 기반 실제 수집 완료!")
        print(f"📈 {result['total_collected']}개 IP 수집")
    else:
        print(f"\n❌ HAR 기반 수집 실패")
        
    return result

if __name__ == "__main__":
    main()