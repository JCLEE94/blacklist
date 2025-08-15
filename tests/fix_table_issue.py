#!/usr/bin/env python3
"""
Fix ip_detections table issue
"""

import sqlite3
from datetime import datetime

def create_ip_detections_table():
    """Create the missing ip_detections table"""
    print("🔧 Creating ip_detections table...")
    
    conn = sqlite3.connect('instance/blacklist.db')
    cursor = conn.cursor()
    
    # Create ip_detections table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            source TEXT NOT NULL,
            detection_type TEXT,
            threat_level INTEGER DEFAULT 5,
            confidence REAL DEFAULT 1.0,
            detection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            country TEXT,
            city TEXT,
            asn TEXT,
            org TEXT,
            description TEXT,
            raw_data TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ip_address, source)
        )
    ''')
    
    print("✅ Table created")
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip_detections_ip ON ip_detections(ip_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip_detections_source ON ip_detections(source)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip_detections_active ON ip_detections(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip_detections_date ON ip_detections(detection_date)')
    
    print("✅ Indexes created")
    
    # Copy data from blacklist_ips to ip_detections
    cursor.execute('''
        INSERT OR IGNORE INTO ip_detections 
        (ip_address, source, detection_type, threat_level, description, detection_date, is_active)
        SELECT 
            ip_address, 
            source, 
            category as detection_type,
            threat_level,
            description,
            added_date as detection_date,
            is_active
        FROM blacklist_ips
        WHERE is_active = 1
    ''')
    
    rows_copied = cursor.rowcount
    print(f"✅ Copied {rows_copied} rows from blacklist_ips")
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM ip_detections")
    total = cursor.fetchone()[0]
    print(f"✅ Total rows in ip_detections: {total}")
    
    # Show sample
    cursor.execute("""
        SELECT ip_address, source, detection_type, threat_level 
        FROM ip_detections 
        LIMIT 5
    """)
    samples = cursor.fetchall()
    
    if samples:
        print("\n📊 Sample data:")
        for ip, source, dtype, threat in samples:
            print(f"  {ip} | {source} | {dtype} | Threat: {threat}")
    
    conn.close()
    
    return total


def test_enhanced_endpoint():
    """Test the enhanced endpoint after fix"""
    print("\n🔍 Testing Enhanced Endpoint...")
    
    from src.core.app_compact import create_app
    import json
    
    app = create_app()
    
    with app.test_client() as client:
        response = client.get('/api/v2/blacklist/enhanced')
        
        if response.status_code == 200:
            data = json.loads(response.get_data(as_text=True))
            
            if data.get('success'):
                entries = data.get('data', [])
                print(f"✅ Enhanced endpoint: {len(entries)} entries")
                
                if entries:
                    print("\n📊 First 5 entries:")
                    for entry in entries[:5]:
                        print(f"  {entry.get('ip_address')} | {entry.get('source')} | {entry.get('detection_type')}")
                
                return True
            else:
                print(f"⚠️ Failed: {data.get('message')}")
        else:
            print(f"❌ HTTP {response.status_code}")
    
    return False


def main():
    print("="*60)
    print("🔧 FIX TABLE ISSUE")
    print("="*60)
    
    # Create table and copy data
    total = create_ip_detections_table()
    
    if total > 0:
        # Test enhanced endpoint
        success = test_enhanced_endpoint()
        
        if success:
            print("\n✅ Table issue fixed successfully!")
        else:
            print("\n⚠️ Table created but endpoint still has issues")
    else:
        print("\n⚠️ No data copied to ip_detections table")
    
    print("="*60)


if __name__ == "__main__":
    main()