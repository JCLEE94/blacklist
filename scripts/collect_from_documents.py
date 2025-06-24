#!/usr/bin/env python3
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
                        if isinstance(ip, str) and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
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
    print(f"\nFound {len(entries)} IPs from Excel files")
    
    # Save to JSON
    with open('data/document_blacklist.json', 'w') as f:
        json.dump(entries, f, indent=2)
