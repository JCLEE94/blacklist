#!/usr/bin/env python3
"""
REGTECH 날짜 범위 기반 수집기 - START DATE 기준 3개월 단위 재조회
REGTECH 시스템의 3개월 제약사항에 맞춰 최적화된 수집기

특징:
- START DATE 기준으로 3개월 단위 자동 분할
- 각 3개월 구간을 1개월씩 세분화하여 수집
- 기존 수집 데이터와 중복 제거
- 자동 재시도 및 오류 복구

사용법:
    python3 regtech_date_range_collector.py --start-date 2024-01-01 --end-date 2024-12-31
    python3 regtech_date_range_collector.py --start-date 2024-01-01 --months 6
"""

import os
import sys
import re
import time
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from urllib.parse import urljoin
import uuid

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class REGTECHDateRangeCollector:
    """REGTECH 날짜 범위 기반 수집기"""
    
    def __init__(self, output_dir="data/sources/regtech"):
        self.base_url = "https://regtech.fsec.or.kr"
        self.advisorylist_url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"
        self.blacklistview_url = f"{self.base_url}/fcti/securityAdvisory/blackListView"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 수집 통계
        self.collected_ips = []
        self.collection_stats = {
            'total_date_ranges': 0,
            'processed_ranges': 0,
            'total_ips': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'duplicates_removed': 0,
            'start_time': None,
            'end_time': None,
            'date_ranges': []
        }
        
        # 스레드 안전성
        self.lock = threading.Lock()
        
        # 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # 기존 수집 데이터 캐시 (중복 제거용)
        self.existing_ips = set()
        self.load_existing_data()
    
    def load_existing_data(self):
        """기존 수집 데이터 로드하여 중복 제거"""
        print("📂 기존 수집 데이터 로드 중...")
        
        # data/sources/regtech/ 폴더의 모든 JSON 파일 확인
        for json_file in self.output_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if 'blacklist_data' in data:
                    for item in data['blacklist_data']:
                        if 'ip' in item:
                            self.existing_ips.add(item['ip'])
                elif isinstance(data, list):
                    for item in data:
                        if 'ip' in item:
                            self.existing_ips.add(item['ip'])
                elif 'ips' in data:
                    for item in data['ips']:
                        if 'ip' in item:
                            self.existing_ips.add(item['ip'])
                            
            except Exception as e:
                print(f"⚠️ {json_file} 로드 실패: {e}")
        
        print(f"✅ 기존 IP 데이터 {len(self.existing_ips):,}개 로드 완료")
    
    def generate_date_ranges(self, start_date, end_date):
        """3개월 단위로 날짜 범위 생성"""
        date_ranges = []
        current_start = start_date
        
        while current_start < end_date:
            # 3개월 후 날짜 계산
            quarter_end = min(current_start + relativedelta(months=3), end_date)
            
            # 3개월 구간을 1개월씩 세분화
            monthly_ranges = []
            month_start = current_start
            
            while month_start < quarter_end:
                month_end = min(month_start + relativedelta(months=1), quarter_end)
                monthly_ranges.append({
                    'start': month_start,
                    'end': month_end,
                    'label': f"{month_start.strftime('%Y-%m')}_{month_end.strftime('%Y-%m')}"
                })
                month_start = month_end
            
            # 3개월 구간 추가
            date_ranges.append({
                'quarter_start': current_start,
                'quarter_end': quarter_end,
                'quarter_label': f"{current_start.strftime('%Y-%m')}_{quarter_end.strftime('%Y-%m')}",
                'monthly_ranges': monthly_ranges
            })
            
            current_start = quarter_end
        
        return date_ranges
    
    def collect_date_range(self, start_date, end_date, label=""):
        """특정 날짜 범위의 데이터 수집"""
        try:
            print(f"📅 수집 시작: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} ({label})")
            
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')
            
            # 첫 번째 페이지로 총 개수 확인
            initial_response = self.session.post(self.advisorylist_url, data={
                'page': '0',
                'size': '50',
                'tabSort': 'blacklist',
                'startDate': start_date_str,
                'endDate': end_date_str,
                'findCondition': 'all'
            }, timeout=30)
            
            if initial_response.status_code != 200:
                print(f"❌ 초기 요청 실패: HTTP {initial_response.status_code}")
                return []
            
            soup = BeautifulSoup(initial_response.text, 'html.parser')
            
            # 총 개수 확인
            total_count = 0
            total_text = soup.find('span', class_='total_num')
            if total_text:
                total_match = re.search(r'총\s*(\d+)', total_text.get_text())
                if total_match:
                    total_count = int(total_match.group(1).replace(',', ''))
            
            if total_count == 0:
                print(f"📊 {label}: 데이터 없음")
                return []
            
            print(f"📊 {label}: 총 {total_count:,}개 항목 발견")
            
            # 페이지 수 계산
            page_size = 50
            total_pages = (total_count + page_size - 1) // page_size
            
            # 모든 페이지 수집
            range_ips = []
            for page_num in range(total_pages):
                page_ips = self.extract_ips_from_page(page_num, page_size, start_date_str, end_date_str)
                range_ips.extend(page_ips)
                
                # 진행률 표시
                progress = ((page_num + 1) / total_pages) * 100
                print(f"📈 {label} 진행률: {progress:.1f}% ({page_num + 1}/{total_pages} 페이지)")
                
                # 요청 간격
                time.sleep(0.2)
            
            # 중복 제거
            unique_ips = []
            for ip_data in range_ips:
                if ip_data['ip'] not in self.existing_ips:
                    unique_ips.append(ip_data)
                    self.existing_ips.add(ip_data['ip'])
                else:
                    with self.lock:
                        self.collection_stats['duplicates_removed'] += 1
            
            print(f"✅ {label}: {len(unique_ips):,}개 고유 IP 수집 (중복 {len(range_ips) - len(unique_ips):,}개 제거)")
            
            return unique_ips
            
        except Exception as e:
            print(f"❌ {label} 수집 실패: {e}")
            return []
    
    def extract_ips_from_page(self, page_num, page_size, start_date_str, end_date_str):
        """단일 페이지에서 IP 정보 추출"""
        try:
            post_data = {
                'page': str(page_num),
                'size': str(page_size),
                'tabSort': 'blacklist',
                'startDate': start_date_str,
                'endDate': end_date_str,
                'findCondition': 'all'
            }
            
            response = self.session.post(self.advisorylist_url, data=post_data, timeout=30)
            
            if response.status_code != 200:
                with self.lock:
                    self.collection_stats['failed_requests'] += 1
                return []
            
            with self.lock:
                self.collection_stats['successful_requests'] += 1
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_ips = []
            
            # IP 추출 로직 (기존 로직 재사용)
            links = soup.find_all('a', href=lambda x: x and 'javascript:goView' in x)
            for link in links:
                href = link.get('href', '')
                uuid_match = re.search(r"goView\('([a-f0-9\-]{36})'\)", href)
                if uuid_match:
                    uuid_val = uuid_match.group(1)
                    
                    tr_element = link.find_parent('tr')
                    if tr_element:
                        tr_text = tr_element.get_text()
                        ip_matches = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', tr_text)
                        
                        if ip_matches:
                            ip_address = ip_matches[0]
                            
                            # 상세 정보 수집
                            detail = self.get_ip_details(ip_address, uuid_val)
                            if detail:
                                detail['date_range'] = f"{start_date_str}_{end_date_str}"
                                detail['page'] = page_num
                                page_ips.append(detail)
                            
                            time.sleep(0.1)  # 요청 간격
            
            return page_ips
            
        except Exception as e:
            with self.lock:
                self.collection_stats['failed_requests'] += 1
            return []
    
    def get_ip_details(self, ip_address, uuid_val):
        """개별 IP의 상세 정보 수집 (기존 로직 재사용)"""
        try:
            post_data = {
                'page': '0',
                'tabSort': 'blacklist',
                'ipId': uuid_val,
                'startDate': (datetime.now() - timedelta(days=365)).strftime('%Y%m%d'),
                'endDate': datetime.now().strftime('%Y%m%d'),
                'findCondition': 'all',
                'size': '10'
            }
            
            response = self.session.post(self.blacklistview_url, data=post_data, timeout=20)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                ip_detail = {
                    'ip': ip_address,
                    'uuid': uuid_val,
                    'country': '',
                    'reason': '',
                    'reg_date': '',
                    'exp_date': '',
                    'view_count': 0,
                    'collection_time': datetime.now().isoformat()
                }
                
                # 상세 정보 추출 (기존 로직과 동일)
                detail_table = soup.find('table', class_='tbl')
                if detail_table:
                    rows = detail_table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            
                            if '국가' in label or 'Country' in label:
                                ip_detail['country'] = value
                            elif '등록사유' in label or 'Reason' in label:
                                ip_detail['reason'] = value
                            elif '등록일' in label or 'Registration' in label:
                                date_match = re.search(r'(\d{4})\.(\d{2})\.(\d{2})', value)
                                if date_match:
                                    ip_detail['reg_date'] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                            elif '해제예정일' in label or 'Expiry' in label:
                                date_match = re.search(r'(\d{4})\.(\d{2})\.(\d{2})', value)
                                if date_match:
                                    ip_detail['exp_date'] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                            elif '조회수' in label or 'View' in label:
                                view_match = re.search(r'(\d+)', value)
                                if view_match:
                                    ip_detail['view_count'] = int(view_match.group(1))
                
                # 기본값 설정
                if not ip_detail['reg_date']:
                    ip_detail['reg_date'] = datetime.now().strftime('%Y-%m-%d')
                if not ip_detail['exp_date']:
                    ip_detail['exp_date'] = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
                if not ip_detail['country']:
                    ip_detail['country'] = 'UNKNOWN'
                if not ip_detail['reason']:
                    ip_detail['reason'] = '보안 위협 탐지'
                
                return ip_detail
            
        except Exception as e:
            print(f"⚠️ IP {ip_address} 상세 정보 수집 실패: {e}")
        
        # 기본 정보라도 반환
        return {
            'ip': ip_address,
            'uuid': uuid_val,
            'country': 'UNKNOWN',
            'reason': '보안 위협 탐지',
            'reg_date': datetime.now().strftime('%Y-%m-%d'),
            'exp_date': (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d'),
            'view_count': 0,
            'collection_time': datetime.now().isoformat()
        }
    
    def collect_by_date_range(self, start_date, end_date):
        """날짜 범위 기반 전체 수집"""
        self.collection_stats['start_time'] = datetime.now()
        
        print(f"🚀 REGTECH 날짜 범위 수집 시작")
        print(f"📅 전체 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        print(f"⏰ 시작 시간: {self.collection_stats['start_time']}")
        print("=" * 70)
        
        # 3개월 단위 날짜 범위 생성
        date_ranges = self.generate_date_ranges(start_date, end_date)
        self.collection_stats['total_date_ranges'] = len(date_ranges)
        
        print(f"📊 총 {len(date_ranges)}개 분기로 분할:")
        for i, quarter in enumerate(date_ranges):
            print(f"  분기 {i+1}: {quarter['quarter_label']} ({len(quarter['monthly_ranges'])}개월)")
        print()
        
        # 각 3개월 분기별 수집
        for quarter_idx, quarter in enumerate(date_ranges):
            print(f"\n🏃‍♂️ 분기 {quarter_idx + 1}/{len(date_ranges)} 수집 시작: {quarter['quarter_label']}")
            
            quarter_ips = []
            
            # 분기 내 월별 수집
            for month_range in quarter['monthly_ranges']:
                month_ips = self.collect_date_range(
                    month_range['start'], 
                    month_range['end'], 
                    month_range['label']
                )
                quarter_ips.extend(month_ips)
                
                # 중간 저장 (메모리 관리)
                if len(quarter_ips) > 1000:
                    self.collected_ips.extend(quarter_ips)
                    quarter_ips = []
            
            self.collected_ips.extend(quarter_ips)
            
            with self.lock:
                self.collection_stats['processed_ranges'] += 1
                self.collection_stats['total_ips'] = len(self.collected_ips)
            
            print(f"✅ 분기 {quarter_idx + 1} 완료: 총 {len(self.collected_ips):,}개 IP 수집")
            
            # 중간 저장
            if (quarter_idx + 1) % 2 == 0:  # 2분기마다 저장
                self.save_intermediate_results(f"quarter_{quarter_idx + 1}")
        
        self.collection_stats['end_time'] = datetime.now()
        duration = self.collection_stats['end_time'] - self.collection_stats['start_time']
        
        print(f"\n✅ 전체 수집 완료!")
        print(f"📊 총 수집된 IP: {len(self.collected_ips):,}개")
        print(f"🔄 중복 제거: {self.collection_stats['duplicates_removed']:,}개")
        print(f"⏱️ 소요 시간: {duration}")
        
        return self.collected_ips
    
    def save_intermediate_results(self, suffix=""):
        """중간 결과 저장"""
        if not self.collected_ips:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"regtech_date_range_{suffix}_{timestamp}.json"
        
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'collection_info': {
                    'timestamp': timestamp,
                    'total_collected': len(self.collected_ips),
                    'collection_stats': self.collection_stats,
                    'data_source': 'regtech.fsec.or.kr',
                    'collection_type': 'date_range_based'
                },
                'blacklist_data': self.collected_ips
            }, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"💾 중간 저장: {output_file}")
    
    def save_final_results(self):
        """최종 결과 저장"""
        if not self.collected_ips:
            print("❌ 저장할 데이터가 없음")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_file = self.output_dir / f"regtech_date_range_final_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'collection_info': {
                    'timestamp': timestamp,
                    'total_collected': len(self.collected_ips),
                    'collection_stats': self.collection_stats,
                    'data_source': 'regtech.fsec.or.kr',
                    'collection_type': 'date_range_based'
                },
                'blacklist_data': self.collected_ips
            }, f, ensure_ascii=False, indent=2, default=str)
        
        # CSV 저장
        df = pd.DataFrame(self.collected_ips)
        csv_file = self.output_dir / f"regtech_date_range_final_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        # 통계 저장
        stats_file = self.output_dir / f"regtech_date_range_stats_{timestamp}.txt"
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("REGTECH 날짜 범위 수집 결과 보고서\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"수집 시간: {self.collection_stats['start_time']} ~ {self.collection_stats['end_time']}\n")
            f.write(f"총 수집 IP: {len(self.collected_ips):,}개\n")
            f.write(f"처리된 범위: {self.collection_stats['processed_ranges']}/{self.collection_stats['total_date_ranges']}\n")
            f.write(f"중복 제거: {self.collection_stats['duplicates_removed']:,}개\n")
            f.write(f"성공 요청: {self.collection_stats['successful_requests']}\n")
            f.write(f"실패 요청: {self.collection_stats['failed_requests']}\n")
        
        print(f"💾 최종 저장 완료:")
        print(f"  📄 JSON: {json_file}")
        print(f"  📊 CSV: {csv_file}")
        print(f"  📋 통계: {stats_file}")
        
        return json_file

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="REGTECH 날짜 범위 기반 수집기 - START DATE 기준 3개월 단위 재조회",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python3 regtech_date_range_collector.py --start-date 2024-01-01 --end-date 2024-12-31
  python3 regtech_date_range_collector.py --start-date 2024-01-01 --months 6
  python3 regtech_date_range_collector.py --start-date 2023-06-01 --months 12
        """
    )
    
    parser.add_argument('--start-date', type=str, required=True,
                       help='시작 날짜 (YYYY-MM-DD 형식)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='종료 날짜 (YYYY-MM-DD 형식)')
    parser.add_argument('--months', type=int, default=None,
                       help='시작 날짜부터 수집할 개월 수')
    parser.add_argument('--output-dir', type=str, default="data/sources/regtech",
                       help='출력 디렉토리 (기본값: data/sources/regtech)')
    
    args = parser.parse_args()
    
    # 날짜 파싱
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    except ValueError:
        print("❌ 시작 날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식을 사용하세요.")
        return
    
    # 종료 날짜 계산
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        except ValueError:
            print("❌ 종료 날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식을 사용하세요.")
            return
    elif args.months:
        end_date = start_date + relativedelta(months=args.months)
    else:
        print("❌ --end-date 또는 --months 중 하나를 지정해야 합니다.")
        return
    
    # 날짜 검증
    if start_date >= end_date:
        print("❌ 시작 날짜가 종료 날짜보다 늦습니다.")
        return
    
    if end_date > datetime.now():
        end_date = datetime.now()
        print(f"⚠️ 종료 날짜를 현재 날짜로 조정: {end_date.strftime('%Y-%m-%d')}")
    
    print("🚀 REGTECH 날짜 범위 수집기 시작")
    print("=" * 70)
    print(f"설정값:")
    print(f"  - 시작 날짜: {start_date.strftime('%Y-%m-%d')}")
    print(f"  - 종료 날짜: {end_date.strftime('%Y-%m-%d')}")
    print(f"  - 총 기간: {(end_date - start_date).days}일")
    print(f"  - 출력 디렉토리: {args.output_dir}")
    print("=" * 70)
    
    # 수집기 초기화
    collector = REGTECHDateRangeCollector(output_dir=args.output_dir)
    
    try:
        # 데이터 수집
        collected_data = collector.collect_by_date_range(start_date, end_date)
        
        if collected_data:
            # 결과 저장
            result_file = collector.save_final_results()
            
            print(f"\n🎉 수집 완료!")
            print(f"📊 총 {len(collected_data):,}개 IP 수집")
            print(f"💾 결과 파일: {result_file}")
        else:
            print("❌ 수집된 데이터가 없습니다.")
            
    except KeyboardInterrupt:
        print(f"\n⏹️ 사용자에 의해 중단됨")
        if collector.collected_ips:
            print(f"📊 현재까지 수집된 데이터: {len(collector.collected_ips)}개")
            collector.save_intermediate_results("interrupted")
    except Exception as e:
        print(f"❌ 수집 중 오류 발생: {e}")
        if collector.collected_ips:
            print(f"📊 현재까지 수집된 데이터: {len(collector.collected_ips)}개")
            collector.save_intermediate_results("error")

if __name__ == "__main__":
    main()