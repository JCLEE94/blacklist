#!/usr/bin/env python3
"""
Save collected data to database
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ['REGTECH_USERNAME'] = 'nextrade'
os.environ['REGTECH_PASSWORD'] = 'test_password'


def collect_and_save():
    """Collect data and save to database"""
    print("\n🔍 Collecting and Saving Data...")
    
    try:
        from src.core.regtech_simple_collector import RegtechSimpleCollector
        
        # Initialize collector
        collector = RegtechSimpleCollector("data")
        print(f"✅ Collector initialized")
        
        # Collect data
        result = collector.collect_from_web()
        
        if result.get('success'):
            print(f"✅ Collection successful: {result.get('total_collected', 0)} IPs")
            
            # The collector already saves data internally
            # Let's check what was saved
            check_saved_data()
        else:
            print(f"⚠️ Collection failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def check_saved_data():
    """Check what data was saved"""
    print("\n🔍 Checking Saved Data...")
    
    try:
        # Check JSON files
        import json
        import glob
        
        json_files = glob.glob("data/regtech/*.json")
        if json_files:
            print(f"✅ Found {len(json_files)} JSON files")
            
            # Read the latest file
            latest_file = sorted(json_files)[-1]
            with open(latest_file, 'r') as f:
                data = json.load(f)
                
            if 'ips' in data:
                print(f"   Latest file has {len(data['ips'])} IPs")
                
                # Show sample
                for ip_info in data['ips'][:3]:
                    print(f"   - {ip_info.get('ip')} | {ip_info.get('reason')} | {ip_info.get('date')}")
                    
                # Save to database
                save_to_database(data['ips'])
        else:
            print("⚠️ No JSON files found")
            
    except Exception as e:
        print(f"❌ Error checking saved data: {e}")


def save_to_database(ips_data):
    """Save IPs to database"""
    print("\n🔍 Saving to Database...")
    
    try:
        conn = sqlite3.connect('instance/blacklist.db')
        cursor = conn.cursor()
        
        saved_count = 0
        for ip_info in ips_data:
            try:
                ip = ip_info.get('ip')
                if not ip:
                    continue
                    
                cursor.execute('''
                    INSERT OR REPLACE INTO blacklist_ips 
                    (ip_address, source, category, threat_level, description, added_date, is_active)
                    VALUES (?, ?, ?, ?, ?, datetime('now'), 1)
                ''', (
                    ip,
                    'REGTECH',
                    ip_info.get('reason', 'unknown'),
                    7,  # Default threat level
                    f"{ip_info.get('country', '')} - {ip_info.get('reason', '')}",
                ))
                saved_count += 1
                
            except Exception as e:
                print(f"   Error saving {ip}: {e}")
                
        conn.commit()
        print(f"✅ Saved {saved_count} IPs to database")
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE source = 'REGTECH'")
        total = cursor.fetchone()[0]
        print(f"   Total REGTECH IPs in database: {total}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")


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
                print(f"   First 5: {ips[:5]}")
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
                
                # Show sources
                sources = {}
                for entry in data['data']:
                    source = entry.get('source', 'unknown')
                    sources[source] = sources.get(source, 0) + 1
                
                print("   By source:")
                for source, count in sources.items():
                    print(f"   - {source}: {count}")
            else:
                print("⚠️ No data in enhanced endpoint")
    except Exception as e:
        print(f"⚠️ Enhanced endpoint error: {e}")


def main():
    """Main function"""
    print("="*60)
    print("📊 Collect and Save Data")
    print("="*60)
    
    # Collect and save data
    collect_and_save()
    
    # Check UI endpoints
    check_ui_endpoints()
    
    print("\n" + "="*60)
    print("✅ Complete")
    print("="*60)


if __name__ == "__main__":
    main()