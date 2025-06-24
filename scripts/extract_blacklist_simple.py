#!/usr/bin/env python3
"""
Simple blacklist data extraction from document files
"""
import json
import os
import re
from pathlib import Path

def extract_blacklist_info():
    """Extract blacklist information from SECUDIUM files"""
    base_path = Path("/home/jclee/dev/blacklist/document")
    
    print("=== SECUDIUM Blacklist Analysis ===\n")
    
    # Check individual view files
    view_files = list(base_path.glob("secudium/*/isap-api/secinfo/view/black_ip/*.html"))
    print(f"Found {len(view_files)} individual blacklist entries\n")
    
    for file in view_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Parse as JSON
                data = json.loads(content)
                
                print(f"Entry ID: {data.get('seq')}")
                print(f"Title: {data.get('title')}")
                print(f"File: {data.get('fileString255')}")
                print(f"IP Field: {data.get('ip')} (metadata, not blacklist)")
                print(f"Content preview: {data.get('content', '')[:100]}...")
                print("-" * 50)
                
        except Exception as e:
            print(f"Error reading {file.name}: {e}")
    
    print("\n=== REGTECH Analysis ===\n")
    
    # Check REGTECH postman collection for download endpoints
    regtech_json = base_path / "regtech/regtech.json"
    if regtech_json.exists():
        with open(regtech_json, 'r', encoding='utf-8') as f:
            postman = json.loads(f.read())
            
        # Look for download endpoints
        download_endpoints = []
        
        def find_endpoints(items):
            for item in items:
                if 'item' in item:
                    find_endpoints(item['item'])
                elif 'request' in item:
                    url = item['request'].get('url', {})
                    if isinstance(url, dict):
                        raw = url.get('raw', '')
                    else:
                        raw = str(url)
                    
                    if 'download' in raw.lower() or 'xlsx' in raw.lower():
                        download_endpoints.append(raw)
        
        find_endpoints(postman.get('item', []))
        
        print("Found download endpoints:")
        for ep in download_endpoints:
            print(f"  - {ep}")
    
    print("\n=== Next Steps ===")
    print("1. The actual blacklist IPs are in Excel files that need to be downloaded")
    print("2. SECUDIUM: Files like '25년 05월 Blacklist 현황.xlsx' contain the IPs")
    print("3. REGTECH: Use the download endpoints to get Excel files with IPs")
    print("4. The 'ip' field in SECUDIUM entries (10.200.200.2) is just metadata")

def create_data_from_documents():
    """Create sample blacklist data based on document structure"""
    print("\n=== Creating Sample Data ===\n")
    
    # Since we can see the data structure but not the actual IPs,
    # let's create a collector that can read from local Excel files
    
    collector_script = """#!/usr/bin/env python3
'''
Document-based blacklist collector
Reads blacklist data from Excel files in the document folder
'''
import pandas as pd
from pathlib import Path
import json
from datetime import datetime

def collect_from_excel():
    '''Collect IPs from Excel files in document folder'''
    doc_path = Path('/home/jclee/dev/blacklist/document')
    blacklist_entries = []
    
    # Look for Excel files
    for excel_file in doc_path.rglob('*.xlsx'):
        print(f"Processing: {excel_file}")
        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Look for columns that might contain IPs
            for col in df.columns:
                if 'ip' in col.lower() or 'address' in col.lower():
                    ips = df[col].dropna().tolist()
                    for ip in ips:
                        # Basic IP validation
                        if isinstance(ip, str) and re.match(r'^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$', ip):
                            blacklist_entries.append({
                                'ip': ip,
                                'source': excel_file.name,
                                'date': datetime.now().isoformat()
                            })
        except Exception as e:
            print(f"Error reading {excel_file}: {e}")
    
    return blacklist_entries

if __name__ == '__main__':
    entries = collect_from_excel()
    print(f"\\nFound {len(entries)} IPs from Excel files")
    
    # Save to JSON
    with open('data/document_blacklist.json', 'w') as f:
        json.dump(entries, f, indent=2)
"""
    
    with open('/home/jclee/dev/blacklist/scripts/collect_from_documents.py', 'w') as f:
        f.write(collector_script)
    
    print("Created: scripts/collect_from_documents.py")
    print("This script will read Excel files from the document folder")

if __name__ == "__main__":
    extract_blacklist_info()
    create_data_from_documents()