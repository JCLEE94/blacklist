#!/usr/bin/env python3
"""
SECUDIUM 고급 수집기 - already.login 오류 처리 및 강제 세션 재설정
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

class AdvancedSecudiumCollector:
    """SECUDIUM 고급 수집기 - 세션 관리 및 강제 로그인"""
    
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
        
    def force_logout_and_login(self, username: str = "nextrade", password: str = "Sprtmxm1@3") -> Dict[str, Any]:
        """강제 로그아웃 후 재로그인"""
        print("🔄 SECUDIUM 강제 세션 재설정 시작...")
        
        # 1단계: 기존 세션 완전 정리
        self._clear_session()
        
        # 2단계: 강제 로그아웃 시도
        self._force_logout()
        
        # 3단계: 새로운 세션으로 로그인
        return self._login_with_force(username, password)
    
    def _clear_session(self):
        """세션 완전 정리"""
        print("   🧹 세션 정리 중...")
        
        # 쿠키 모두 삭제
        self.session.cookies.clear()
        
        # 새로운 세션 생성
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        self.token = None
        print("      ✅ 세션 정리 완료")
    
    def _force_logout(self):
        """강제 로그아웃 시도"""
        print("   🚪 강제 로그아웃 시도...")
        
        logout_endpoints = [
            "/isap-api/logout",
            "/logout", 
            "/isap-api/session/clear",
            "/api/logout"
        ]
        
        for endpoint in logout_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = self.session.post(url, timeout=10)
                print(f"      📤 로그아웃 시도: {endpoint} -> {response.status_code}")
            except:
                continue
        
        # 대기 시간
        time.sleep(2)
        print("      ✅ 강제 로그아웃 완료")
    
    def _login_with_force(self, username: str, password: str) -> Dict[str, Any]:
        """강제 로그인 플래그와 함께 로그인"""
        print("   🔐 강제 로그인 시도...")
        
        login_url = f"{self.base_url}/isap-api/loginProcess"
        
        # 여러 로그인 방법 시도
        login_attempts = [
            # 방법 1: 기본 강제 로그인
            {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'N',
                'login_name': username,
                'password': password,
                'otp_value': '',
                'force_login': 'Y',
                'logout_other': 'Y'
            },
            # 방법 2: 확장 강제 로그인
            {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'N',
                'login_name': username,
                'password': password,
                'otp_value': '',
                'force': 'true',
                'override': 'true',
                'disconnect_others': 'true'
            },
            # 방법 3: 단순 재로그인
            {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'N',
                'login_name': username,
                'password': password,
                'otp_value': ''
            }
        ]
        
        for i, login_data in enumerate(login_attempts, 1):
            print(f"      🎯 로그인 방법 {i} 시도...")
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': self.base_url,
                'Referer': f"{self.base_url}/login",
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            try:
                response = self.session.post(login_url, data=login_data, headers=headers, timeout=15)
                
                print(f"         응답: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        print(f"         결과: {result}")
                        
                        response_data = result.get('response', {})
                        
                        # 성공 체크 - error=False이고 token이 있으면 성공
                        if response_data.get('error') == False and 'token' in response_data:
                            print("         ✅ 로그인 성공!")
                            
                            self.token = response_data['token']
                            self.session.headers.update({
                                'X-Auth-Token': self.token,
                                'Authorization': f'Bearer {self.token}'
                            })
                            
                            return {
                                'success': True,
                                'token': self.token,
                                'session': self.session,
                                'method': f'force_login_{i}'
                            }
                        
                        # already.login이 아닌 다른 오류인 경우 계속 시도
                        elif response_data.get('code') != 'already.login':
                            print(f"         ⚠️ 다른 오류: {response_data.get('message', 'Unknown')}")
                            continue
                        
                        print(f"         ❌ 여전히 already.login 오류")
                        
                    except json.JSONDecodeError:
                        print(f"         ⚠️ JSON 파싱 실패")
                        continue
                
            except Exception as e:
                print(f"         ❌ 요청 예외: {e}")
                continue
            
            # 방법 간 대기
            time.sleep(1)
        
        print("   ❌ 모든 강제 로그인 방법 실패")
        return {'success': False, 'error': 'All force login attempts failed'}
    
    def collect_blacklist_data(self) -> Dict[str, Any]:
        """토큰을 이용한 블랙리스트 데이터 수집"""
        print("📋 SECUDIUM 블랙리스트 데이터 수집...")
        
        if not self.token:
            print("   ❌ 토큰이 없습니다. 먼저 로그인하세요.")
            return {'success': False, 'error': 'No token available'}
        
        # 여러 블랙리스트 엔드포인트 시도
        blacklist_endpoints = [
            "/isap-api/secinfo/list/black_ip",
            "/api/secinfo/list/black_ip",
            "/isap-api/blacklist",
            "/api/blacklist/ips",
            "/isap-api/threat/blacklist"
        ]
        
        for endpoint in blacklist_endpoints:
            print(f"   🎯 엔드포인트 시도: {endpoint}")
            
            url = f"{self.base_url}{endpoint}"
            
            # 다양한 파라미터 조합 시도
            param_sets = [
                {'page': 0, 'size': 1000, 'sort': 'regDate,desc'},
                {'page': 0, 'limit': 1000},
                {'offset': 0, 'limit': 1000},
                {}  # 파라미터 없음
            ]
            
            for params in param_sets:
                try:
                    headers = {
                        'Accept': 'application/json, text/javascript, */*; q=0.01',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-Auth-Token': self.token,
                        'Authorization': f'Bearer {self.token}',
                        'Referer': f"{self.base_url}/secinfo/black_ip"
                    }
                    
                    response = self.session.get(url, params=params, headers=headers, timeout=15)
                    
                    print(f"      📊 응답: {response.status_code} (params: {params})")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            
                            # 데이터 구조 분석
                            if isinstance(data, dict):
                                # 페이징된 데이터
                                if 'content' in data or 'data' in data or 'rows' in data:
                                    rows = data.get('content', data.get('data', data.get('rows', [])))
                                    if rows:
                                        parsed_data = self._parse_blacklist_data(rows)
                                        return {
                                            'success': True,
                                            'data': parsed_data,
                                            'endpoint': endpoint,
                                            'total_entries': len(rows),
                                            'parsed_ips': len(parsed_data)
                                        }
                                # 직접 리스트
                                elif isinstance(data, list):
                                    parsed_data = self._parse_blacklist_data(data)
                                    return {
                                        'success': True,
                                        'data': parsed_data,
                                        'endpoint': endpoint,
                                        'total_entries': len(data),
                                        'parsed_ips': len(parsed_data)
                                    }
                            
                            elif isinstance(data, list):
                                parsed_data = self._parse_blacklist_data(data)
                                return {
                                    'success': True,
                                    'data': parsed_data,
                                    'endpoint': endpoint,
                                    'total_entries': len(data),
                                    'parsed_ips': len(parsed_data)
                                }
                            
                            print(f"      ⚠️ 예상과 다른 데이터 구조: {type(data)}")
                            
                        except json.JSONDecodeError:
                            print(f"      ⚠️ JSON 파싱 실패")
                            continue
                    
                    elif response.status_code == 401:
                        print(f"      ⚠️ 인증 오류 - 토큰 만료 가능")
                        return {'success': False, 'error': 'Authentication failed - token expired'}
                    
                except Exception as e:
                    print(f"      ❌ 요청 예외: {e}")
                    continue
        
        print("   ❌ 모든 블랙리스트 엔드포인트 실패")
        return {'success': False, 'error': 'All blacklist endpoints failed'}
    
    def _parse_blacklist_data(self, data: List[Dict]) -> List[Dict[str, Any]]:
        """블랙리스트 데이터 파싱"""
        parsed_data = []
        
        for item in data:
            ip_value = None
            
            # IP 필드 찾기 - 다양한 가능한 필드명
            ip_fields = ['ip', 'ipAddress', 'ip_address', 'sourceIp', 'target_ip', 'malicious_ip']
            
            for field in ip_fields:
                if field in item and item[field]:
                    ip_value = str(item[field]).strip()
                    break
            
            # 데이터가 리스트 형태인 경우
            if not ip_value and isinstance(item, dict) and 'data' in item:
                item_data = item['data']
                if isinstance(item_data, list) and len(item_data) > 0:
                    # 첫 번째 요소가 IP일 가능성
                    potential_ip = str(item_data[0]).strip()
                    if self._is_valid_ip(potential_ip):
                        ip_value = potential_ip
            
            if ip_value and self._is_valid_ip(ip_value):
                parsed_data.append({
                    'ip': ip_value,
                    'source': 'SECUDIUM',
                    'detection_date': datetime.now().strftime('%Y-%m-%d'),
                    'attack_type': 'SK쉴더스 탐지',
                    'country': item.get('country', 'Unknown'),
                    'collection_method': 'advanced_api_token'
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
                        'Advanced Force Login Collection',
                        item.get('collection_method', 'advanced_force_login')
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
    
    def run_complete_collection(self) -> Dict[str, Any]:
        """완전한 SECUDIUM 수집 프로세스"""
        print("🚀 SECUDIUM 고급 강제 수집 시작")
        print("=" * 60)
        
        # 1단계: 강제 로그아웃 후 재로그인
        login_result = self.force_logout_and_login()
        if not login_result['success']:
            print(f"❌ 강제 로그인 실패: {login_result['error']}")
            return login_result
        
        print(f"✅ 로그인 성공 (방법: {login_result.get('method', 'unknown')})")
        print(f"🔑 토큰: {self.token[:20]}...")
        
        # 2단계: 블랙리스트 데이터 수집
        collection_result = self.collect_blacklist_data()
        if not collection_result['success']:
            print(f"❌ 데이터 수집 실패: {collection_result['error']}")
            return collection_result
        
        print(f"✅ 데이터 수집 성공")
        print(f"📊 엔드포인트: {collection_result['endpoint']}")
        print(f"📊 전체 엔트리: {collection_result['total_entries']}개")
        print(f"📊 파싱된 IP: {collection_result['parsed_ips']}개")
        
        # 3단계: 데이터베이스 저장
        if collection_result.get('data'):
            db_result = self.save_to_database(collection_result['data'])
            collection_result['database'] = db_result
        
        print("\n" + "=" * 60)
        print("📊 SECUDIUM 고급 수집 결과")
        print("=" * 60)
        print(f"📊 수집 IP: {collection_result.get('parsed_ips', 0)}개")
        
        if 'database' in collection_result:
            db_stats = collection_result['database']
            if db_stats.get('success'):
                print(f"💾 DB 저장: {db_stats['inserted']}개 신규 추가")
                print(f"📊 전체 DB: {db_stats['total_count']}개 IP")
        
        print("🎉 SECUDIUM 고급 수집 완료!")
        
        return collection_result

def main():
    """메인 실행"""
    collector = AdvancedSecudiumCollector()
    result = collector.run_complete_collection()
    return result

if __name__ == "__main__":
    main()