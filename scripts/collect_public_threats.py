#!/usr/bin/env python3
"""
공개 위협 정보 수집기
다양한 공개 위협 인텔리전스 소스에서 출처 정보 포함한 데이터 수집
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import re
from dataclasses import dataclass

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.models import BlacklistEntry

logger = logging.getLogger(__name__)


@dataclass
class ThreatSource:
    """위협 정보 소스 정의"""
    name: str
    url: str
    format: str  # 'ip_list', 'csv', 'json'
    description: str
    update_frequency: str
    reliability: str  # 'high', 'medium', 'low'


class PublicThreatCollector:
    """공개 위협 정보 수집기"""
    
    def __init__(self):
        self.output_dir = Path("data/blacklist/sources/public")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 공개 위협 정보 소스 목록
        self.threat_sources = [
            ThreatSource(
                name="emergingthreats",
                url="https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt",
                format="ip_list",
                description="Emerging Threats 블랙리스트 IP",
                update_frequency="daily",
                reliability="high"
            ),
            ThreatSource(
                name="cybercrime-tracker",
                url="http://cybercrime-tracker.net/ccam.php",
                format="ip_list", 
                description="Cybercrime Tracker 악성 IP",
                update_frequency="hourly",
                reliability="high"
            ),
            ThreatSource(
                name="blocklist.de",
                url="https://www.blocklist.de/downloads/exportcsv.php",
                format="csv",
                description="Blocklist.de SSH/FTP 공격 IP",
                update_frequency="daily",
                reliability="medium"
            ),
            ThreatSource(
                name="greensnow",
                url="https://blocklist.greensnow.co/greensnow.txt",
                format="ip_list",
                description="Green Snow 스팸/공격 IP",
                update_frequency="daily", 
                reliability="medium"
            ),
            ThreatSource(
                name="bruteforceblocker",
                url="https://danger.rulez.sk/projects/bruteforceblocker/blist.php",
                format="ip_list",
                description="Brute Force 공격 IP",
                update_frequency="daily",
                reliability="medium"
            )
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ThreatIntelCollector/1.0)'
        })
    
    def collect_all_sources(self) -> Dict[str, Any]:
        """모든 소스에서 데이터 수집"""
        result = {
            'success': True,
            'total_collected': 0,
            'sources_processed': [],
            'errors': []
        }
        
        all_entries = []
        
        for source in self.threat_sources:
            try:
                logger.info(f"수집 시작: {source.name} - {source.description}")
                entries = self._collect_from_source(source)
                
                if entries:
                    all_entries.extend(entries)
                    result['total_collected'] += len(entries)
                    result['sources_processed'].append({
                        'name': source.name,
                        'count': len(entries),
                        'description': source.description
                    })
                    
                    # 개별 소스 파일 저장
                    self._save_source_data(entries, source)
                    
                    logger.info(f"{source.name} 수집 완료: {len(entries)}개 IP")
                else:
                    result['errors'].append(f"{source.name}: 데이터 수집 실패")
                    
            except Exception as e:
                error_msg = f"{source.name} 수집 중 오류: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        # 통합 데이터 저장
        if all_entries:
            self._save_unified_data(all_entries)
            logger.info(f"공개 위협 정보 통합 완료: 총 {len(all_entries)}개 IP")
        
        result['success'] = len(all_entries) > 0
        return result
    
    def _collect_from_source(self, source: ThreatSource) -> List[Dict[str, Any]]:
        """개별 소스에서 데이터 수집"""
        try:
            response = self.session.get(source.url, timeout=30)
            response.raise_for_status()
            
            if source.format == "ip_list":
                return self._parse_ip_list(response.text, source)
            elif source.format == "csv":
                return self._parse_csv(response.text, source)
            elif source.format == "json":
                return self._parse_json(response.text, source)
            
        except Exception as e:
            logger.error(f"{source.name} 데이터 수집 실패: {e}")
            return []
    
    def _parse_ip_list(self, content: str, source: ThreatSource) -> List[Dict[str, Any]]:
        """IP 목록 형태 데이터 파싱"""
        entries = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            # 주석이나 빈 줄 건너뛰기
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            # IP 주소 추출
            ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', line)
            if ip_match:
                ip = ip_match.group(0)
                
                # BlacklistEntry 생성
                entry = BlacklistEntry(
                    ip_address=ip,
                    source=f"public_{source.name}",
                    reason=f"{source.description}에서 탐지",
                    threat_level=self._determine_threat_level(source),
                    is_active=True,
                    source_details={
                        'source_name': source.name,
                        'source_url': source.url,
                        'collection_method': 'public_api',
                        'collection_time': datetime.now().isoformat(),
                        'reliability': source.reliability,
                        'update_frequency': source.update_frequency,
                        'format': source.format,
                        'description': source.description
                    },
                    detection_months=[datetime.now().strftime('%Y-%m')],
                    first_seen=datetime.now().strftime('%Y-%m'),
                    last_seen=datetime.now().strftime('%Y-%m')
                )
                
                entries.append(entry.to_dict())
        
        return entries
    
    def _parse_csv(self, content: str, source: ThreatSource) -> List[Dict[str, Any]]:
        """CSV 형태 데이터 파싱"""
        entries = []
        lines = content.split('\n')
        
        # 헤더 건너뛰기
        for line in lines[1:]:
            if not line.strip():
                continue
            
            parts = line.split(',')
            if len(parts) > 0:
                ip = parts[0].strip().strip('"')
                
                # IP 주소 유효성 검사
                if re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', ip):
                    # 추가 정보 추출
                    reason = parts[1].strip().strip('"') if len(parts) > 1 else source.description
                    country = parts[2].strip().strip('"') if len(parts) > 2 else None
                    
                    entry = BlacklistEntry(
                        ip_address=ip,
                        source=f"public_{source.name}",
                        reason=reason,
                        country=country,
                        threat_level=self._determine_threat_level(source),
                        is_active=True,
                        source_details={
                            'source_name': source.name,
                            'source_url': source.url,
                            'collection_method': 'public_csv',
                            'collection_time': datetime.now().isoformat(),
                            'reliability': source.reliability,
                            'update_frequency': source.update_frequency,
                            'format': source.format,
                            'description': source.description,
                            'csv_fields': len(parts)
                        },
                        detection_months=[datetime.now().strftime('%Y-%m')],
                        first_seen=datetime.now().strftime('%Y-%m'),
                        last_seen=datetime.now().strftime('%Y-%m')
                    )
                    
                    entries.append(entry.to_dict())
        
        return entries
    
    def _parse_json(self, content: str, source: ThreatSource) -> List[Dict[str, Any]]:
        """JSON 형태 데이터 파싱"""
        entries = []
        
        try:
            data = json.loads(content)
            
            # JSON 구조에 따라 파싱 로직 조정 필요
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'ip' in item:
                        entry = BlacklistEntry(
                            ip_address=item['ip'],
                            source=f"public_{source.name}",
                            reason=item.get('reason', source.description),
                            country=item.get('country'),
                            threat_level=self._determine_threat_level(source),
                            is_active=True,
                            source_details={
                                'source_name': source.name,
                                'source_url': source.url,
                                'collection_method': 'public_json',
                                'collection_time': datetime.now().isoformat(),
                                'reliability': source.reliability,
                                'update_frequency': source.update_frequency,
                                'format': source.format,
                                'description': source.description,
                                'original_data': item
                            },
                            detection_months=[datetime.now().strftime('%Y-%m')],
                            first_seen=datetime.now().strftime('%Y-%m'),
                            last_seen=datetime.now().strftime('%Y-%m')
                        )
                        
                        entries.append(entry.to_dict())
            
        except json.JSONDecodeError as e:
            logger.error(f"{source.name} JSON 파싱 실패: {e}")
        
        return entries
    
    def _determine_threat_level(self, source: ThreatSource) -> str:
        """소스 기반 위험도 판정"""
        reliability_map = {
            'high': 'high',
            'medium': 'medium', 
            'low': 'low'
        }
        return reliability_map.get(source.reliability, 'medium')
    
    def _save_source_data(self, entries: List[Dict[str, Any]], source: ThreatSource):
        """개별 소스 데이터 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 파일 저장
        json_file = self.output_dir / f"public_{source.name}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'source_name': source.name,
                    'source_url': source.url,
                    'description': source.description,
                    'collection_time': timestamp,
                    'total_entries': len(entries),
                    'reliability': source.reliability,
                    'update_frequency': source.update_frequency
                },
                'entries': entries
            }, f, ensure_ascii=False, indent=2)
        
        # 간단한 IP 목록도 저장
        txt_file = self.output_dir / f"public_{source.name}_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"# {source.description}\n")
            f.write(f"# 소스: {source.url}\n")
            f.write(f"# 수집 시간: {timestamp}\n")
            f.write(f"# 총 {len(entries)}개 IP\n\n")
            
            for entry in entries:
                f.write(f"{entry['ip']}\n")
        
        logger.info(f"{source.name} 데이터 저장 완료: {json_file}")
    
    def _save_unified_data(self, all_entries: List[Dict[str, Any]]):
        """통합 데이터 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 중복 IP 제거
        unique_entries = {}
        for entry in all_entries:
            ip = entry['ip']
            if ip not in unique_entries:
                unique_entries[ip] = entry
            else:
                # 여러 소스에서 발견된 경우 정보 병합
                existing = unique_entries[ip]
                existing['source_details']['multiple_sources'] = True
                existing['source_details']['additional_sources'] = existing['source_details'].get('additional_sources', [])
                existing['source_details']['additional_sources'].append(entry['source_details'])
        
        unified_entries = list(unique_entries.values())
        
        # 통합 JSON 파일 저장
        unified_file = self.output_dir / f"public_unified_threats_{timestamp}.json"
        with open(unified_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'source': 'public_threats',
                    'collection_time': timestamp,
                    'total_unique_ips': len(unified_entries),
                    'total_raw_entries': len(all_entries),
                    'sources_count': len(self.threat_sources),
                    'description': '공개 위협 인텔리전스 통합 데이터베이스'
                },
                'blacklist_entries': unified_entries
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"공개 위협 정보 통합 데이터 저장 완료: {unified_file}")
        logger.info(f"고유 IP: {len(unified_entries)}개, 원본 항목: {len(all_entries)}개")


def main():
    """메인 실행 함수"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    collector = PublicThreatCollector()
    
    try:
        logger.info("공개 위협 정보 수집 시작")
        result = collector.collect_all_sources()
        
        print(f"\n=== 공개 위협 정보 수집 결과 ===")
        print(f"성공: {result['success']}")
        print(f"총 수집: {result['total_collected']}개 IP")
        print(f"처리된 소스: {len(result['sources_processed'])}개")
        
        if result['sources_processed']:
            print(f"\n=== 소스별 수집 현황 ===")
            for source_info in result['sources_processed']:
                print(f"- {source_info['name']}: {source_info['count']}개 - {source_info['description']}")
        
        if result['errors']:
            print(f"\n=== 오류 ===")
            for error in result['errors']:
                print(f"- {error}")
        
    except Exception as e:
        logger.error(f"수집 중 오류 발생: {e}")


if __name__ == "__main__":
    main()