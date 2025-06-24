#!/usr/bin/env python3
"""
실제 위협 인텔리전스 소스에서 블랙리스트 IP 수집
공개된 위협 피드에서 실제 악성 IP 데이터 수집
"""
import requests
import json
import logging
import re
import os
from datetime import datetime
import time
from urllib3.exceptions import InsecureRequestWarning

# SSL 경고 무시
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealThreatIPCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.all_ips = set()
        
        # 데이터 저장 경로
        script_dir = os.path.dirname(__file__)
        self.data_dir = os.path.join(script_dir, '..', 'data', 'blacklist')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def validate_ip(self, ip):
        """IP 주소 유효성 검사"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                num = int(part)
                if not (0 <= num <= 255):
                    return False
            
            # 내부 IP 및 특수 IP 제외
            if (ip.startswith('10.') or 
                ip.startswith('192.168.') or
                ip.startswith('172.16.') or ip.startswith('172.17.') or ip.startswith('172.18.') or
                ip.startswith('172.19.') or ip.startswith('172.20.') or ip.startswith('172.21.') or
                ip.startswith('172.22.') or ip.startswith('172.23.') or ip.startswith('172.24.') or
                ip.startswith('172.25.') or ip.startswith('172.26.') or ip.startswith('172.27.') or
                ip.startswith('172.28.') or ip.startswith('172.29.') or ip.startswith('172.30.') or
                ip.startswith('172.31.') or
                ip.startswith('127.') or
                ip.startswith('0.') or
                ip.startswith('169.254.') or
                ip.startswith('224.') or ip.startswith('225.') or ip.startswith('226.') or
                ip.startswith('227.') or ip.startswith('228.') or ip.startswith('229.') or
                ip.startswith('230.') or ip.startswith('231.') or ip.startswith('232.') or
                ip.startswith('233.') or ip.startswith('234.') or ip.startswith('235.') or
                ip.startswith('236.') or ip.startswith('237.') or ip.startswith('238.') or
                ip.startswith('239.') or
                ip == '255.255.255.255'):
                return False
                
            return True
        except ValueError:
            return False
    
    def collect_from_abuse_ch(self):
        """Abuse.ch 위협 피드에서 수집"""
        logger.info("Collecting from Abuse.ch...")
        
        sources = [
            'https://feodotracker.abuse.ch/downloads/ipblocklist.txt',
            'https://sslbl.abuse.ch/blacklist/sslipblacklist.txt',
            'https://urlhaus.abuse.ch/downloads/csv/',
            'https://bazaar.abuse.ch/export/txt/ips/'
        ]
        
        collected = 0
        
        for source in sources:
            try:
                logger.info(f"  Fetching: {source}")
                resp = self.session.get(source, timeout=30)
                
                if resp.status_code == 200:
                    content = resp.text
                    
                    # IP 패턴 추출
                    ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                    ips = ip_pattern.findall(content)
                    
                    valid_ips = 0
                    for ip in ips:
                        if self.validate_ip(ip):
                            self.all_ips.add(ip)
                            valid_ips += 1
                    
                    logger.info(f"    Added {valid_ips} valid IPs")
                    collected += valid_ips
                    
                    time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"  Error fetching {source}: {e}")
        
        logger.info(f"Abuse.ch total: {collected} IPs")
        return collected
    
    def collect_from_blocklist_de(self):
        """Blocklist.de에서 수집"""
        logger.info("Collecting from Blocklist.de...")
        
        sources = [
            'https://lists.blocklist.de/lists/all.txt',
            'https://lists.blocklist.de/lists/ssh.txt',
            'https://lists.blocklist.de/lists/mail.txt',
            'https://lists.blocklist.de/lists/apache.txt',
            'https://lists.blocklist.de/lists/bots.txt'
        ]
        
        collected = 0
        
        for source in sources:
            try:
                logger.info(f"  Fetching: {source}")
                resp = self.session.get(source, timeout=30)
                
                if resp.status_code == 200:
                    lines = resp.text.strip().split('\n')
                    
                    valid_ips = 0
                    for line in lines:
                        line = line.strip()
                        if self.validate_ip(line):
                            self.all_ips.add(line)
                            valid_ips += 1
                    
                    logger.info(f"    Added {valid_ips} valid IPs")
                    collected += valid_ips
                    
                    time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"  Error fetching {source}: {e}")
        
        logger.info(f"Blocklist.de total: {collected} IPs")
        return collected
    
    def collect_from_greensnow(self):
        """GreenSnow에서 수집"""
        logger.info("Collecting from GreenSnow...")
        
        try:
            url = 'https://blocklist.greensnow.co/greensnow.txt'
            logger.info(f"  Fetching: {url}")
            
            resp = self.session.get(url, timeout=30)
            
            if resp.status_code == 200:
                lines = resp.text.strip().split('\n')
                
                valid_ips = 0
                for line in lines:
                    line = line.strip()
                    if self.validate_ip(line):
                        self.all_ips.add(line)
                        valid_ips += 1
                
                logger.info(f"    Added {valid_ips} valid IPs")
                logger.info(f"GreenSnow total: {valid_ips} IPs")
                return valid_ips
                
        except Exception as e:
            logger.error(f"  Error fetching GreenSnow: {e}")
        
        return 0
    
    def collect_from_talos(self):
        """Cisco Talos에서 수집"""
        logger.info("Collecting from Cisco Talos...")
        
        try:
            url = 'https://www.talosintelligence.com/documents/ip-blacklist'
            logger.info(f"  Fetching: {url}")
            
            resp = self.session.get(url, timeout=30)
            
            if resp.status_code == 200:
                content = resp.text
                
                # IP 패턴 추출
                ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                ips = ip_pattern.findall(content)
                
                valid_ips = 0
                for ip in ips:
                    if self.validate_ip(ip):
                        self.all_ips.add(ip)
                        valid_ips += 1
                
                logger.info(f"    Added {valid_ips} valid IPs")
                logger.info(f"Talos total: {valid_ips} IPs")
                return valid_ips
                
        except Exception as e:
            logger.error(f"  Error fetching Talos: {e}")
        
        return 0
    
    def collect_from_spamhaus(self):
        """Spamhaus DROP 리스트에서 수집"""
        logger.info("Collecting from Spamhaus...")
        
        sources = [
            'https://www.spamhaus.org/drop/drop.txt',
            'https://www.spamhaus.org/drop/edrop.txt'
        ]
        
        collected = 0
        
        for source in sources:
            try:
                logger.info(f"  Fetching: {source}")
                resp = self.session.get(source, timeout=30)
                
                if resp.status_code == 200:
                    lines = resp.text.strip().split('\n')
                    
                    valid_ips = 0
                    for line in lines:
                        line = line.strip()
                        # 주석 라인 제외
                        if line.startswith(';') or not line:
                            continue
                            
                        # CIDR 표기에서 IP 추출
                        if '/' in line:
                            ip = line.split('/')[0].strip()
                        else:
                            ip = line.split()[0].strip() if line.split() else line
                        
                        if self.validate_ip(ip):
                            self.all_ips.add(ip)
                            valid_ips += 1
                    
                    logger.info(f"    Added {valid_ips} valid IPs")
                    collected += valid_ips
                    
                    time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"  Error fetching {source}: {e}")
        
        logger.info(f"Spamhaus total: {collected} IPs")
        return collected
    
    def collect_from_emergingthreats(self):
        """Emerging Threats에서 수집"""
        logger.info("Collecting from Emerging Threats...")
        
        sources = [
            'https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt',
            'https://rules.emergingthreats.net/blockrules/compromised-ips.txt'
        ]
        
        collected = 0
        
        for source in sources:
            try:
                logger.info(f"  Fetching: {source}")
                resp = self.session.get(source, timeout=30)
                
                if resp.status_code == 200:
                    content = resp.text
                    
                    # IP 패턴 추출
                    ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                    ips = ip_pattern.findall(content)
                    
                    valid_ips = 0
                    for ip in ips:
                        if self.validate_ip(ip):
                            self.all_ips.add(ip)
                            valid_ips += 1
                    
                    logger.info(f"    Added {valid_ips} valid IPs")
                    collected += valid_ips
                    
                    time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"  Error fetching {source}: {e}")
        
        logger.info(f"Emerging Threats total: {collected} IPs")
        return collected
    
    def collect_all_sources(self):
        """모든 소스에서 수집"""
        logger.info("Starting collection from all threat intelligence sources...")
        
        start_time = time.time()
        
        # 각 소스에서 수집
        abuse_ch_count = self.collect_from_abuse_ch()
        blocklist_de_count = self.collect_from_blocklist_de()
        greensnow_count = self.collect_from_greensnow()
        talos_count = self.collect_from_talos()
        spamhaus_count = self.collect_from_spamhaus()
        emerging_threats_count = self.collect_from_emergingthreats()
        
        end_time = time.time()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"THREAT INTELLIGENCE COLLECTION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Abuse.ch:         {abuse_ch_count:,} IPs")
        logger.info(f"Blocklist.de:     {blocklist_de_count:,} IPs")
        logger.info(f"GreenSnow:        {greensnow_count:,} IPs")
        logger.info(f"Cisco Talos:      {talos_count:,} IPs")
        logger.info(f"Spamhaus:         {spamhaus_count:,} IPs")
        logger.info(f"Emerging Threats: {emerging_threats_count:,} IPs")
        logger.info(f"{'='*60}")
        logger.info(f"TOTAL UNIQUE IPs: {len(self.all_ips):,}")
        logger.info(f"Collection time:  {end_time - start_time:.1f} seconds")
        logger.info(f"{'='*60}")
        
        return len(self.all_ips)
    
    def save_blacklist_data(self):
        """블랙리스트 데이터 저장"""
        if not self.all_ips:
            logger.error("No IPs to save")
            return False
        
        # 현재 월 디렉토리 생성
        current_month = datetime.now().strftime("%Y_%m")
        month_dir = os.path.join(self.data_dir, f"by_detection_month/{current_month}")
        os.makedirs(month_dir, exist_ok=True)
        
        # 월별 블랙리스트 저장
        monthly_file = os.path.join(month_dir, "blacklist.txt")
        with open(monthly_file, 'w') as f:
            for ip in sorted(self.all_ips):
                f.write(f"{ip}\n")
        
        # 전체 활성 블랙리스트 저장
        all_active_file = os.path.join(self.data_dir, "all_ips.txt")
        with open(all_active_file, 'w') as f:
            for ip in sorted(self.all_ips):
                f.write(f"{ip}\n")
        
        # 통계 파일 업데이트
        stats_file = os.path.join(os.path.dirname(self.data_dir), "stats.json")
        stats = {
            "last_update": datetime.now().isoformat(),
            "total_ips": len(self.all_ips),
            "current_month_ips": len(self.all_ips),
            "update_count": 1,
            "sources": [
                "Abuse.ch",
                "Blocklist.de", 
                "GreenSnow",
                "Cisco Talos",
                "Spamhaus",
                "Emerging Threats"
            ]
        }
        
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"\nReal threat intelligence data saved:")
        logger.info(f"  - Monthly file: {monthly_file}")
        logger.info(f"  - All active:   {all_active_file}")
        logger.info(f"  - Statistics:   {stats_file}")
        
        # 샘플 IP 출력
        sample_ips = list(sorted(self.all_ips))[:20]
        logger.info(f"\nSample threat IPs:")
        for i, ip in enumerate(sample_ips, 1):
            logger.info(f"  {i:2d}. {ip}")
        
        if len(self.all_ips) > 20:
            logger.info(f"  ... and {len(self.all_ips) - 20:,} more")
        
        return True

def main():
    """메인 함수"""
    logger.info("="*60)
    logger.info("REAL THREAT INTELLIGENCE BLACKLIST COLLECTOR")
    logger.info("="*60)
    
    collector = RealThreatIPCollector()
    
    # 모든 소스에서 데이터 수집
    total_ips = collector.collect_all_sources()
    
    if total_ips > 0:
        # 데이터 저장
        if collector.save_blacklist_data():
            logger.info(f"\n✅ SUCCESS: {total_ips:,} real threat IPs collected and saved!")
            return True
        else:
            logger.error("❌ FAILED: Could not save collected data")
            return False
    else:
        logger.error("❌ FAILED: No threat IPs collected")
        return False

if __name__ == "__main__":
    if main():
        print("\n🎯 실제 위협 인텔리전스 블랙리스트 수집 완료!")
    else:
        print("\n💥 위협 인텔리전스 수집 실패")