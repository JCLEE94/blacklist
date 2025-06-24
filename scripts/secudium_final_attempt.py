#!/usr/bin/env python3
"""
SECUDIUM 최종 시도 - 성공 HAR 분석 기반 구현
성공적인 로그인 HAR 파일을 분석해서 정확한 처리 로직 구현
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List
import sqlite3

class SecudiumFinalCollector:
    """SECUDIUM 최종 수집기 - 성공 HAR 분석 기반"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        self.base_url = "https://secudium.skinfosec.co.kr"
        self.token = None
        
    def analyze_existing_session(self) -> Dict[str, Any]:
        """기존 세션 상태 분석"""
        print("🔍 기존 세션 상태 분석...")
        
        # 1단계: 로그인 페이지 접근하여 세션 쿠키 확인
        try:
            login_page = self.session.get(f"{self.base_url}/login", timeout=15)
            print(f"   📊 로그인 페이지: {login_page.status_code}")
            
            # 세션 쿠키 확인
            cookies = self.session.cookies
            print(f"   🍪 현재 쿠키: {len(cookies)}개")
            
            for cookie in cookies:
                print(f"      - {cookie.name}: {cookie.value[:20]}...")
            
            return {'status': 'ready', 'cookies_count': len(cookies)}
            
        except Exception as e:
            print(f"   ❌ 세션 분석 실패: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def handle_already_login_scenario(self, username: str = "nextrade", password: str = "Sprtmxm1@3") -> Dict[str, Any]:
        """already.login 시나리오 전용 처리"""
        print("🔄 already.login 시나리오 처리...")
        
        # HAR 파일에서 추출한 정확한 로그인 데이터
        login_url = f"{self.base_url}/isap-api/loginProcess"
        login_data = {
            'lang': 'ko',
            'is_otp': 'N',
            'is_expire': 'N',
            'login_name': username,
            'password': password,
            'otp_value': ''
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/login",
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        try:
            # 첫 번째 로그인 시도
            print("   1️⃣ 첫 번째 로그인 시도...")
            response = self.session.post(login_url, data=login_data, headers=headers, timeout=15)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"   📊 응답: {result}")
                    
                    response_data = result.get('response', {})
                    
                    # already.login 오류 처리
                    if response_data.get('code') == 'already.login':
                        print("   🔄 already.login 감지 - JavaScript 로직 기반 처리")
                        
                        # HAR 파일에서 본 성공적인 경우와 동일하게 처리
                        # JavaScript에서는 이미 존재하는 세션 쿠키를 활용
                        
                        # 기존 세션으로 메인 페이지 접근 시도
                        print("   2️⃣ 기존 세션으로 메인 페이지 접근...")
                        main_response = self.session.get(f"{self.base_url}/", timeout=15)
                        
                        if main_response.status_code == 200 and '장홍준' in main_response.text:
                            print("   ✅ 기존 세션으로 접속 성공!")
                            
                            # 세션 쿠키에서 토큰 추출 시도
                            self._extract_session_token()
                            
                            return {
                                'success': True,
                                'method': 'existing_session',
                                'session': self.session,
                                'note': 'Used existing session from already.login scenario'
                            }
                        
                        # 강제 로그인 시도 (다른 파라미터)
                        print("   3️⃣ 강제 로그인 파라미터 시도...")
                        force_attempts = [
                            # 대소문자 변경
                            {'LANG': 'ko', 'IS_OTP': 'N', 'IS_EXPIRE': 'N', 'LOGIN_NAME': username, 'PASSWORD': password, 'OTP_VALUE': ''},
                            # 추가 파라미터
                            {**login_data, 'force': 'true'},
                            {**login_data, 'override_session': 'Y'},
                            # 순서 변경
                            {'login_name': username, 'password': password, 'lang': 'ko', 'is_otp': 'N', 'is_expire': 'N', 'otp_value': ''}
                        ]
                        
                        for i, attempt_data in enumerate(force_attempts, 1):
                            print(f"      🎯 강제 시도 {i}: {list(attempt_data.keys())}")
                            
                            force_response = self.session.post(login_url, data=attempt_data, headers=headers, timeout=15)
                            
                            if force_response.status_code == 200:
                                try:
                                    force_result = force_response.json()
                                    force_response_data = force_result.get('response', {})
                                    
                                    # 성공 체크
                                    if force_response_data.get('error') == False:
                                        print(f"      ✅ 강제 로그인 성공! (시도 {i})")
                                        
                                        if 'token' in force_response_data:
                                            self.token = force_response_data['token']
                                            self.session.headers.update({
                                                'X-Auth-Token': self.token,
                                                'Authorization': f'Bearer {self.token}'
                                            })
                                        
                                        return {
                                            'success': True,
                                            'method': f'force_login_{i}',
                                            'token': self.token,
                                            'session': self.session
                                        }
                                    
                                    elif force_response_data.get('code') != 'already.login':
                                        print(f"      ⚠️ 새로운 오류: {force_response_data}")
                                        
                                except json.JSONDecodeError:
                                    print(f"      ⚠️ JSON 파싱 실패")
                                    continue
                            
                            time.sleep(1)  # 시도 간 대기
                        
                        print("   ❌ 모든 강제 로그인 방법 실패")
                        return {'success': False, 'error': 'All force login attempts failed'}
                    
                    # 정상 성공 처리
                    elif response_data.get('error') == False:
                        print("   ✅ 정상 로그인 성공!")
                        
                        if 'token' in response_data:
                            self.token = response_data['token']
                            self.session.headers.update({
                                'X-Auth-Token': self.token,
                                'Authorization': f'Bearer {self.token}'
                            })
                        
                        return {
                            'success': True,
                            'method': 'normal_login',
                            'token': self.token,
                            'session': self.session
                        }
                    
                    else:
                        print(f"   ❌ 기타 로그인 오류: {response_data}")
                        return {'success': False, 'error': response_data}
                        
                except json.JSONDecodeError:
                    print("   ⚠️ JSON 파싱 실패")
                    return {'success': False, 'error': 'JSON parsing failed'}
            
            else:
                print(f"   ❌ HTTP 오류: {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            print(f"   ❌ 로그인 예외: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_session_token(self):
        """세션 쿠키에서 토큰 추출"""
        try:
            # 쿠키에서 토큰 찾기
            for cookie in self.session.cookies:
                if 'token' in cookie.name.lower() or 'auth' in cookie.name.lower():
                    self.token = cookie.value
                    print(f"   🔑 세션에서 토큰 추출: {self.token[:20]}...")
                    
                    self.session.headers.update({
                        'X-Auth-Token': self.token,
                        'Authorization': f'Bearer {self.token}'
                    })
                    break
                    
        except Exception as e:
            print(f"   ⚠️ 토큰 추출 실패: {e}")
    
    def collect_blacklist_with_session(self) -> Dict[str, Any]:
        """세션을 이용한 블랙리스트 수집"""
        print("📋 세션 기반 블랙리스트 수집...")
        
        # 다양한 엔드포인트와 방법 시도
        collection_attempts = [
            # 방법 1: 기본 API
            {
                'url': f"{self.base_url}/isap-api/secinfo/list/black_ip",
                'params': {'page': 0, 'size': 1000},
                'headers': {'X-Requested-With': 'XMLHttpRequest'}
            },
            # 방법 2: 페이지 직접 접근
            {
                'url': f"{self.base_url}/secinfo/black_ip",
                'params': {},
                'headers': {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
            },
            # 방법 3: 다른 API 패턴
            {
                'url': f"{self.base_url}/api/blacklist",
                'params': {'limit': 1000},
                'headers': {'X-Requested-With': 'XMLHttpRequest'}
            }
        ]
        
        for i, attempt in enumerate(collection_attempts, 1):
            print(f"   {i}️⃣ 수집 방법 {i} 시도: {attempt['url']}")
            
            try:
                headers = {**self.session.headers, **attempt['headers']}
                response = self.session.get(attempt['url'], params=attempt['params'], headers=headers, timeout=15)
                
                print(f"      📊 응답: {response.status_code}")
                
                if response.status_code == 200:
                    # JSON 응답 처리
                    if 'application/json' in response.headers.get('Content-Type', ''):
                        try:
                            data = response.json()
                            if isinstance(data, dict) and ('content' in data or 'data' in data or 'rows' in data):
                                rows = data.get('content', data.get('data', data.get('rows', [])))
                                if rows:
                                    print(f"      ✅ JSON 데이터 {len(rows)}개 발견!")
                                    parsed_data = self._parse_json_blacklist(rows)
                                    return {
                                        'success': True,
                                        'data': parsed_data,
                                        'method': f'json_api_{i}',
                                        'total': len(parsed_data)
                                    }
                        except json.JSONDecodeError:
                            pass
                    
                    # HTML 응답 처리
                    elif 'text/html' in response.headers.get('Content-Type', ''):
                        if 'black' in response.text.lower() and 'ip' in response.text.lower():
                            print(f"      ✅ HTML 페이지에서 블랙리스트 데이터 감지!")
                            parsed_data = self._parse_html_blacklist(response.text)
                            if parsed_data:
                                return {
                                    'success': True,
                                    'data': parsed_data,
                                    'method': f'html_page_{i}',
                                    'total': len(parsed_data)
                                }
                
                elif response.status_code == 401:
                    print(f"      ⚠️ 인증 오류 - 토큰 재설정 필요")
                    continue
                
            except Exception as e:
                print(f"      ❌ 수집 예외: {e}")
                continue
        
        print("   ❌ 모든 수집 방법 실패")
        return {'success': False, 'error': 'All collection methods failed'}
    
    def _parse_json_blacklist(self, data: List[Dict]) -> List[Dict[str, Any]]:
        """JSON 블랙리스트 데이터 파싱"""
        parsed_data = []
        
        for item in data:
            ip_value = None
            
            # 다양한 IP 필드 검색
            for field in ['ip', 'ipAddress', 'ip_address', 'sourceIp', 'target_ip', 'malicious_ip']:
                if field in item and item[field]:
                    ip_value = str(item[field]).strip()
                    break
            
            if ip_value and self._is_valid_ip(ip_value):
                parsed_data.append({
                    'ip': ip_value,
                    'source': 'SECUDIUM',
                    'detection_date': datetime.now().strftime('%Y-%m-%d'),
                    'attack_type': 'SK쉴더스 탐지',
                    'country': item.get('country', 'Unknown'),
                    'collection_method': 'session_json_api'
                })
        
        return parsed_data
    
    def _parse_html_blacklist(self, html_content: str) -> List[Dict[str, Any]]:
        """HTML 페이지에서 블랙리스트 데이터 파싱"""
        import re
        
        # IP 주소 패턴 찾기
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = re.findall(ip_pattern, html_content)
        
        parsed_data = []
        for ip in set(ips):  # 중복 제거
            if self._is_valid_ip(ip):
                parsed_data.append({
                    'ip': ip,
                    'source': 'SECUDIUM',
                    'detection_date': datetime.now().strftime('%Y-%m-%d'),
                    'attack_type': 'HTML 페이지 추출',
                    'country': 'Unknown',
                    'collection_method': 'session_html_parsing'
                })
        
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
            # 내부 IP 제외
            if ip.startswith(('192.168.', '10.', '172.16.', '127.')):
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
                        'Final Session Based Collection',
                        item.get('collection_method', 'session_final')
                    ))
                    
                    if cursor.rowcount > 0:
                        inserted += 1
                        
                except Exception as e:
                    print(f"   ⚠️ 데이터 삽입 오류: {e}")
                    continue
            
            conn.commit()
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
    
    def run_final_collection(self) -> Dict[str, Any]:
        """최종 SECUDIUM 수집 실행"""
        print("🚀 SECUDIUM 최종 수집 시작")
        print("=" * 60)
        
        # 1단계: 세션 상태 분석
        session_status = self.analyze_existing_session()
        print(f"📊 세션 상태: {session_status}")
        
        # 2단계: already.login 시나리오 처리
        login_result = self.handle_already_login_scenario()
        if not login_result['success']:
            print(f"❌ 로그인 처리 실패: {login_result['error']}")
            return login_result
        
        print(f"✅ 로그인 처리 성공 (방법: {login_result.get('method', 'unknown')})")
        
        # 3단계: 블랙리스트 수집
        collection_result = self.collect_blacklist_with_session()
        if not collection_result['success']:
            print(f"❌ 데이터 수집 실패: {collection_result['error']}")
            return collection_result
        
        print(f"✅ 데이터 수집 성공")
        print(f"📊 수집 방법: {collection_result['method']}")
        print(f"📊 수집 IP: {collection_result['total']}개")
        
        # 4단계: 데이터베이스 저장
        if collection_result.get('data'):
            db_result = self.save_to_database(collection_result['data'])
            collection_result['database'] = db_result
        
        print("\n" + "=" * 60)
        print("📊 SECUDIUM 최종 수집 결과")
        print("=" * 60)
        print(f"📊 수집 IP: {collection_result.get('total', 0)}개")
        
        if 'database' in collection_result:
            db_stats = collection_result['database']
            if db_stats.get('success'):
                print(f"💾 DB 저장: {db_stats['inserted']}개 신규 추가")
                print(f"📊 전체 DB: {db_stats['total_count']}개 IP")
        
        print("🎉 SECUDIUM 최종 수집 완료!")
        
        return collection_result

def main():
    """메인 실행"""
    collector = SecudiumFinalCollector()
    result = collector.run_final_collection()
    return result

if __name__ == "__main__":
    main()