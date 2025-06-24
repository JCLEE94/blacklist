#!/usr/bin/env python3
"""
Simple REGTECH collection script to test basic functionality
"""
import sys
import os
# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.core.regtech_collector import RegtechCollector
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def main():
    print("🚀 Starting REGTECH collection...")
    
    # Initialize collector
    collector = RegtechCollector(data_dir='data/sources')
    
    # Try to collect data (limited to 3 pages for testing)
    try:
        result = collector.collect_from_web(max_pages=3, parallel_workers=1)
        
        print("\n📊 Collection Results:")
        print(f"Total collected: {result['total_collected']}")
        print(f"Successful: {result['successful_collections']}")
        print(f"Failed: {result['failed_collections']}")
        print(f"Duplicates: {result['duplicate_count']}")
        
        # Import to database if successful
        if result['total_collected'] > 0:
            print("\n💾 Importing to database...")
            import sqlite3
            conn = sqlite3.connect('instance/blacklist.db')
            cursor = conn.cursor()
            
            # Get collected data
            collected_file = max(
                [f for f in os.listdir('data/sources/regtech') if f.endswith('.json')],
                key=lambda x: os.path.getctime(os.path.join('data/sources/regtech', x))
            )
            
            import json
            with open(os.path.join('data/sources/regtech', collected_file), 'r') as f:
                data = json.load(f)
            
            # Insert into database
            for entry in data[:100]:  # Limit to 100 for testing
                cursor.execute('''
                    INSERT OR IGNORE INTO blacklist_ip 
                    (ip, country, attack_type, source, detection_date, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    entry['ip'],
                    entry.get('country', 'KR'),
                    entry.get('attack_type', 'Unknown'),
                    'REGTECH',
                    entry.get('detection_date', '2025-06-19'),
                    'active'
                ))
            
            conn.commit()
            count = cursor.execute('SELECT COUNT(*) FROM blacklist_ip').fetchone()[0]
            print(f"✅ Database now contains {count} IPs")
            conn.close()
            
    except Exception as e:
        print(f"❌ Collection failed: {e}")
        print("\nTrying alternative: Looking for existing REGTECH data files...")
        
        # Check for existing data files
        regtech_dir = 'data/sources/regtech'
        if os.path.exists(regtech_dir):
            files = [f for f in os.listdir(regtech_dir) if f.endswith('.json')]
            if files:
                print(f"Found {len(files)} existing data files")
                # Use the most recent one
                latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(regtech_dir, x)))
                print(f"Using: {latest_file}")
                
                # Load and import
                import json
                with open(os.path.join(regtech_dir, latest_file), 'r') as f:
                    data = json.load(f)
                print(f"Found {len(data)} IPs in file")
                
                # Import to database
                import sqlite3
                conn = sqlite3.connect('instance/blacklist.db')
                cursor = conn.cursor()
                
                imported = 0
                for entry in data[:100]:  # First 100 IPs
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO blacklist_ip 
                            (ip, country, attack_type, source, detection_date, status)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            entry['ip'],
                            entry.get('country', 'KR'),
                            entry.get('attack_type', 'Unknown'),
                            'REGTECH',
                            entry.get('detection_date', '2025-06-19'),
                            'active'
                        ))
                        imported += 1
                    except Exception as e:
                        print(f"Skip IP {entry['ip']}: {e}")
                
                conn.commit()
                count = cursor.execute('SELECT COUNT(*) FROM blacklist_ip').fetchone()[0]
                print(f"✅ Imported {imported} IPs. Database now contains {count} IPs")
                conn.close()

if __name__ == '__main__':
    main()