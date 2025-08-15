#!/usr/bin/env python3
"""
Load collected JSON data into database
"""

import os
import sys
import json
import sqlite3
import glob
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_json_to_database():
    """Load all JSON files to database"""
    print("\n📊 Loading Collected Data to Database...")
    
    try:
        # Find all JSON files
        json_files = glob.glob("data/regtech/*.json")
        if not json_files:
            print("⚠️ No JSON files found in data/regtech/")
            return
            
        print(f"✅ Found {len(json_files)} JSON files")
        
        # Get the latest file
        latest_file = sorted(json_files)[-1]
        print(f"   Loading latest: {os.path.basename(latest_file)}")
        
        # Read JSON data
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get IPs from data
        ips_data = data.get('data', data.get('ips', []))
        if not ips_data:
            print("⚠️ No IP data found in JSON")
            return
            
        print(f"   Found {len(ips_data)} IPs in JSON")
        
        # Connect to database
        conn = sqlite3.connect('instance/blacklist.db')
        cursor = conn.cursor()
        
        # Clear existing REGTECH data (optional)
        cursor.execute("DELETE FROM blacklist_ips WHERE source = 'REGTECH'")
        print("   Cleared existing REGTECH data")
        
        # Insert new data
        saved_count = 0
        for ip_info in ips_data:
            try:
                ip = ip_info.get('ip')
                if not ip:
                    continue
                
                # Prepare data
                country = ip_info.get('country', 'Unknown')
                reason = ip_info.get('reason', 'blacklist')
                date = ip_info.get('date', datetime.now().strftime('%Y-%m-%d'))
                
                # Map reason to category and threat level
                category = reason.lower() if reason else 'unknown'
                threat_level = 7  # Default threat level
                
                if 'malware' in category:
                    threat_level = 9
                elif 'botnet' in category:
                    threat_level = 8
                elif 'phishing' in category:
                    threat_level = 7
                elif 'spam' in category:
                    threat_level = 6
                
                # Insert to database
                cursor.execute('''
                    INSERT OR REPLACE INTO blacklist_ips 
                    (ip_address, source, category, threat_level, description, added_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (
                    ip,
                    'REGTECH',
                    category,
                    threat_level,
                    f"{country} - {reason}",
                    datetime.now(),
                ))
                
                saved_count += 1
                
                if saved_count % 100 == 0:
                    print(f"   Saved {saved_count} IPs...")
                    
            except Exception as e:
                print(f"   Error saving IP {ip}: {e}")
        
        # Commit changes
        conn.commit()
        print(f"✅ Successfully saved {saved_count} IPs to database")
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE source = 'REGTECH'")
        total = cursor.fetchone()[0]
        print(f"   Total REGTECH IPs in database: {total}")
        
        # Show sample
        cursor.execute("""
            SELECT ip_address, category, threat_level 
            FROM blacklist_ips 
            WHERE source = 'REGTECH' 
            LIMIT 5
        """)
        samples = cursor.fetchall()
        if samples:
            print("\n   Sample data:")
            for ip, cat, threat in samples:
                print(f"   - {ip} | {cat} | Threat: {threat}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def check_ui_endpoints():
    """Check if data appears in UI endpoints"""
    print("\n🔍 Checking UI Endpoints...")
    
    import requests
    
    base_url = "http://localhost:32542"
    
    # Check active IPs
    try:
        resp = requests.get(f"{base_url}/api/blacklist/active")
        if resp.status_code == 200:
            ips = resp.text.strip().split('\n')
            if ips and ips[0]:
                print(f"✅ Active IPs endpoint: {len(ips)} IPs")
                print(f"   First 5 IPs:")
                for ip in ips[:5]:
                    print(f"   - {ip}")
            else:
                print("⚠️ No active IPs")
    except Exception as e:
        print(f"⚠️ Active IPs error: {e}")
    
    # Check enhanced endpoint
    try:
        resp = requests.get(f"{base_url}/api/v2/blacklist/enhanced")
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success') and data.get('data'):
                print(f"✅ Enhanced endpoint: {len(data['data'])} entries")
                
                # Show by source
                sources = {}
                for entry in data['data']:
                    source = entry.get('source', 'unknown')
                    sources[source] = sources.get(source, 0) + 1
                
                print("   By source:")
                for source, count in sources.items():
                    print(f"   - {source}: {count}")
                    
                # Show sample
                print("\n   Sample entries:")
                for entry in data['data'][:3]:
                    print(f"   - {entry.get('ip_address')} | {entry.get('source')} | {entry.get('category')}")
            else:
                print("⚠️ No data in enhanced endpoint")
    except Exception as e:
        print(f"⚠️ Enhanced endpoint error: {e}")
    
    # Check FortiGate endpoint
    try:
        resp = requests.get(f"{base_url}/api/fortigate")
        if resp.status_code == 200:
            text = resp.text
            if text and len(text) > 10:
                lines = text.strip().split('\n')
                print(f"✅ FortiGate endpoint: {len(lines)} lines")
                print(f"   First 3 lines:")
                for line in lines[:3]:
                    print(f"   - {line[:100]}...")
            else:
                print("⚠️ No data in FortiGate endpoint")
    except Exception as e:
        print(f"⚠️ FortiGate endpoint error: {e}")


def main():
    """Main function"""
    print("="*60)
    print("🚀 Load Collected Data to Database")
    print("="*60)
    
    # Load JSON data to database
    load_json_to_database()
    
    # Check UI endpoints
    check_ui_endpoints()
    
    print("\n" + "="*60)
    print("✅ Complete")
    print("="*60)


if __name__ == "__main__":
    main()