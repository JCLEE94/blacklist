#!/usr/bin/env python3
"""
Extract blacklist data from document folder
"""
import json
import os
from datetime import datetime
from pathlib import Path

def extract_secudium_data():
    """Extract SECUDIUM blacklist data from document files"""
    base_path = Path("/home/jclee/dev/blacklist/document/secudium")
    
    # Read the list data
    list_file = base_path / "secudium.skinfosec.co.kr/isap-api/secinfo/list/black_ip.html"
    if list_file.exists():
        with open(list_file, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
            rows = data.get('rows', [])
            print(f"\nFound {len(rows)} SECUDIUM blacklist entries:")
            
            for row in rows[:5]:  # Show first 5
                entry_data = row.get('data', [])
                if len(entry_data) >= 5:
                    title = entry_data[2]
                    author = entry_data[3]
                    date = entry_data[4]
                    print(f"  - {title} by {author} ({date})")
    
    # Read individual entries
    view_path = base_path / "secudium.skinfosec.co.kr/isap-api/secinfo/view/black_ip"
    if view_path.exists():
        print("\nAnalyzing individual entries:")
        for file in view_path.glob("*.html"):
            with open(file, 'r', encoding='utf-8') as f:
                try:
                    entry = json.loads(f.read())
                    print(f"\n  Entry {entry.get('seq')}:")
                    print(f"    Title: {entry.get('title')}")
                    print(f"    File: {entry.get('fileString255')}")
                    print(f"    IP Field: {entry.get('ip')}")  # This seems to be metadata, not blacklist IP
                    print(f"    Date: {datetime.fromtimestamp(entry.get('regDate', 0)/1000).strftime('%Y-%m-%d %H:%M:%S')}")
                except Exception as e:
                    print(f"    Error reading {file}: {e}")

def extract_regtech_data():
    """Extract REGTECH data from document files"""
    base_path = Path("/home/jclee/dev/blacklist/document/regtech")
    
    # Read Postman collection
    postman_file = base_path / "regtech.json"
    if postman_file.exists():
        with open(postman_file, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
            print("\n\nREGTECH API Endpoints from Postman collection:")
            
            def extract_endpoints(items, prefix=""):
                for item in items:
                    if 'item' in item:
                        # It's a folder
                        extract_endpoints(item['item'], prefix + item.get('name', '') + "/")
                    elif 'request' in item:
                        # It's a request
                        req = item['request']
                        url = req.get('url', {})
                        if isinstance(url, dict):
                            raw_url = url.get('raw', '')
                        else:
                            raw_url = str(url)
                        
                        # Look for interesting endpoints
                        if any(keyword in raw_url.lower() for keyword in ['blacklist', 'black', 'ip', 'download', 'xlsx', 'advisory']):
                            print(f"  - {req.get('method', 'GET')} {raw_url}")
            
            extract_endpoints(data.get('item', []))

def find_actual_blacklist_ips():
    """Look for files that might contain actual IP addresses"""
    base_path = Path("/home/jclee/dev/blacklist/document")
    
    print("\n\nSearching for files that might contain IP addresses:")
    
    # Look for data files
    for ext in ['*.txt', '*.csv', '*.json', '*.dat']:
        for file in base_path.rglob(ext):
            # Skip known non-IP files
            if any(skip in str(file) for skip in ['css', 'js', 'font', 'vendor', 'DataURI']):
                continue
                
            # Check file size (skip very large files)
            if file.stat().st_size > 10 * 1024 * 1024:  # 10MB
                continue
                
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1024)  # Read first 1KB
                    
                    # Simple IP pattern check
                    import re
                    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                    ips = re.findall(ip_pattern, content)
                    
                    # Filter out common non-blacklist IPs
                    filtered_ips = [ip for ip in ips if not (
                        ip.startswith('192.168.') or 
                        ip.startswith('10.') or 
                        ip.startswith('127.') or
                        ip.startswith('0.') or
                        ip.endswith('.0')
                    )]
                    
                    if filtered_ips:
                        print(f"\n  {file.relative_to(base_path)}:")
                        print(f"    Found IPs: {', '.join(filtered_ips[:5])}...")
                        
            except Exception as e:
                pass

if __name__ == "__main__":
    extract_secudium_data()
    extract_regtech_data()
    find_actual_blacklist_ips()