#!/usr/bin/env python3
"""
REGTECH 기간별 수집 가능여부 파악 테스트
다양한 날짜 범위로 수집해서 기간별 데이터 가용성 확인
"""

import os
import re
import json
import requests
import sys
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv

sys.path.insert(0, '/home/jclee/app/blacklist')
load_dotenv()

def test_period_collection():
    """다양한 기간으로 수집 테스트"""
    
    username = os.getenv('REGTECH_USERNAME', '')
    password = os.getenv('REGTECH_PASSWORD', '')
    
    if not username or not password:
        print("❌ REGTECH 자격증명이 설정되지 않음")
        return []
    
    base_url = "https://regtech.fsec.or.kr"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    period_results = {}
    
    try:
        # 1. 로그인
        print(f"🔐 REGTECH 로그인: {username}")
        session.get(f'{base_url}/login/loginForm')
        
        verify_data = {'memberId': username, 'memberPw': password}
        session.headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        verify_resp = session.post(f"{base_url}/member/findOneMember", data=verify_data)
        if verify_resp.status_code != 200:
            print(f"❌ 사용자 확인 실패")
            return period_results
        
        login_form_data = {
            'username': username, 'password': password, 'login_error': '',
            'txId': '', 'token': '', 'memberId': '', 'smsTimeExcess': 'N'
        }
        
        login_resp = session.post(f"{base_url}/login/addLogin", data=login_form_data, allow_redirects=True)
        if login_resp.status_code != 200 or 'main' not in login_resp.url:
            print("❌ 로그인 실패")
            return period_results
        
        print("✅ 로그인 성공")
        
        # 2. 다양한 기간별 수집 테스트
        print("\n📅 기간별 수집 테스트...")
        
        # 테스트할 기간들
        test_periods = [
            (1, "1일"),
            (7, "1주일"),
            (14, "2주일"),
            (30, "1개월"),
            (60, "2개월"),
            (90, "3개월"),
            (180, "6개월"),
            (365, "1년"),
            (730, "2년")
        ]
        
        base_date = datetime.now()
        
        for days_back, period_name in test_periods:
            print(f"\n  🔍 {period_name} 테스트 ({days_back}일)")
            
            start_date = base_date - timedelta(days=days_back)
            end_date = base_date
            
            # 기간별 수집 시도
            ips = collect_by_period(session, base_url, start_date, end_date)
            
            period_results[period_name] = {
                "days_back": days_back,
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "ip_count": len(ips),
                "available": len(ips) > 0,
                "sample_ips": ips[:5] if ips else []
            }
            
            if ips:
                print(f"    ✅ {len(ips)}개 IP 수집 성공")
                print(f"    📋 샘플: {ips[:3] if len(ips) >= 3 else ips}")
            else:
                print(f"    ❌ 데이터 없음")
        
        # 3. 특정 월별 세밀한 테스트
        print(f"\n📊 월별 세밀한 테스트...")
        monthly_results = {}
        
        for months_back in range(1, 13):  # 최근 12개월
            month_start = base_date.replace(day=1) - timedelta(days=months_back*30)
            month_end = month_start + timedelta(days=30)
            
            month_name = month_start.strftime('%Y년 %m월')
            print(f"  📅 {month_name}")
            
            month_ips = collect_by_period(session, base_url, month_start, month_end)
            
            monthly_results[month_name] = {
                "start_date": month_start.strftime('%Y-%m-%d'),
                "end_date": month_end.strftime('%Y-%m-%d'),
                "ip_count": len(month_ips),
                "available": len(month_ips) > 0
            }
            
            if month_ips:
                print(f"    ✅ {len(month_ips)}개")
            else:
                print(f"    ❌ 없음")
        
        # 4. 결과 분석 및 출력
        print(f"\n" + "="*80)
        print(f"📊 기간별 수집 가능여부 분석 결과")
        print(f"="*80)
        
        print(f"\n🗓️ 기간별 결과:")
        for period_name, result in period_results.items():
            status = "✅ 가능" if result["available"] else "❌ 불가"
            print(f"  {period_name:8} ({result['days_back']:3d}일): {status} - {result['ip_count']:3d}개 IP")
        
        print(f"\n📈 월별 결과:")
        available_months = 0
        total_months = len(monthly_results)
        
        for month_name, result in monthly_results.items():
            if result["available"]:
                available_months += 1
                status = "✅"
            else:
                status = "❌"
            print(f"  {month_name}: {status} {result['ip_count']:3d}개")
        
        print(f"\n📋 요약:")
        print(f"  - 수집 가능한 기간: {sum(1 for r in period_results.values() if r['available'])}/{len(period_results)}개")
        print(f"  - 수집 가능한 월: {available_months}/{total_months}개월")
        
        # 최적 수집 기간 추천
        max_ips = max((r["ip_count"] for r in period_results.values()), default=0)
        optimal_periods = [p for p, r in period_results.items() if r["ip_count"] == max_ips and max_ips > 0]
        
        if optimal_periods:
            print(f"  - 최적 수집 기간: {optimal_periods[0]} ({max_ips}개 IP)")
        
        # 데이터 가용성 패턴 분석
        print(f"\n🔍 데이터 가용성 패턴:")
        
        # 단기간 데이터 (1주일 이하)
        short_term = [r for p, r in period_results.items() if r["days_back"] <= 7]
        short_available = sum(1 for r in short_term if r["available"])
        print(f"  - 단기간 (1주일 이하): {short_available}/{len(short_term)} 가능")
        
        # 중기간 데이터 (1주일-3개월)
        mid_term = [r for p, r in period_results.items() if 7 < r["days_back"] <= 90]
        mid_available = sum(1 for r in mid_term if r["available"])
        print(f"  - 중기간 (1주일-3개월): {mid_available}/{len(mid_term)} 가능")
        
        # 장기간 데이터 (3개월 이상)
        long_term = [r for p, r in period_results.items() if r["days_back"] > 90]
        long_available = sum(1 for r in long_term if r["available"])
        print(f"  - 장기간 (3개월 이상): {long_available}/{len(long_term)} 가능")
        
        return {
            "period_results": period_results,
            "monthly_results": monthly_results,
            "summary": {
                "max_ips": max_ips,
                "optimal_periods": optimal_periods,
                "total_periods_tested": len(period_results),
                "available_periods": sum(1 for r in period_results.values() if r["available"]),
                "available_months": available_months,
                "total_months": total_months
            }
        }
    
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        return {"error": str(e)}
    
    finally:
        session.close()


def collect_by_period(session, base_url, start_date, end_date):
    """특정 기간 데이터 수집"""
    try:
        advisory_url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        
        post_data = {
            'page': '1',
            'size': '1000',
            'rows': '1000',
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'tabSort': 'blacklist',
            'findCondition': 'all',
            'findKeyword': ''
        }
        
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        resp = session.post(advisory_url, data=post_data)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            return extract_ips_from_soup(soup)
        
        return []
    
    except Exception as e:
        return []


def extract_ips_from_soup(soup):
    """BeautifulSoup에서 IP 추출"""
    ips = []
    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    
    # 모든 텍스트에서 IP 찾기
    all_text = soup.get_text()
    found_ips = ip_pattern.findall(all_text)
    
    for ip in found_ips:
        if is_valid_ip(ip):
            ips.append(ip)
    
    return list(set(ips))  # 중복 제거


def is_valid_ip(ip):
    """IP 주소 유효성 검사"""
    try:
        octets = ip.split('.')
        if len(octets) != 4:
            return False
        
        for octet in octets:
            num = int(octet)
            if not (0 <= num <= 255):
                return False
        
        # 로컬/예약 IP 제외
        if ip.startswith(('127.', '192.168.', '10.', '172.', '0.', '255.')):
            return False
        
        # 멀티캐스트/브로드캐스트 제외
        first_octet = int(octets[0])
        if first_octet >= 224:
            return False
        
        return True
    
    except:
        return False


if __name__ == "__main__":
    print("🚀 REGTECH 기간별 수집 가능여부 테스트")
    print("="*80)
    
    # 기간별 수집 테스트 실행
    results = test_period_collection()
    
    if results and "error" not in results:
        print(f"\n✅ 기간별 수집 테스트 완료!")
        
        # JSON 파일로 결과 저장
        try:
            with open('regtech_period_analysis.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"📄 결과가 regtech_period_analysis.json에 저장되었습니다")
        except Exception as e:
            print(f"❌ 결과 저장 실패: {e}")
        
        # 수집 권장사항
        summary = results.get("summary", {})
        if summary.get("optimal_periods"):
            print(f"\n💡 수집 권장사항:")
            print(f"  - 최적 기간: {summary['optimal_periods'][0]}")
            print(f"  - 최대 IP 수: {summary['max_ips']}개")
            print(f"  - 가용 기간: {summary['available_periods']}/{summary['total_periods_tested']}개")
    else:
        print(f"\n❌ 기간별 수집 테스트 실패")
        if "error" in results:
            print(f"오류: {results['error']}")
    
    print(f"\n🔍 기간별 수집 가능여부 파악 완료!")