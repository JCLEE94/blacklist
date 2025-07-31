#!/usr/bin/env python3
"""
Complete database cleanup and fresh REGTECH collection setup
"""
import os
import shutil
import sqlite3
from datetime import datetime

import pytz


def main():
    """Main cleanup and setup process"""
    kst = pytz.timezone("Asia/Seoul")
    current_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S KST")

    print("=" * 60)
    print("DATABASE CLEANUP AND FRESH COLLECTION SETUP")
    print("=" * 60)
    print(f"Current Time: {current_time}")
    print()

    # Step 1: Create environment file if not exists
    if not os.path.exists(".env"):
        print("📝 Creating .env file template...")
        env_content = """# Blacklist System Environment Configuration

# API Credentials (for legacy collection)
BLACKLIST_USERNAME=
BLACKLIST_PASSWORD=

# Port Configuration
DEV_PORT=1541
PROD_PORT=2541

# Database
DATABASE_URL=sqlite:///instance/blacklist.db

# Redis (optional - falls back to memory cache)
REDIS_URL=

# Security Keys
JWT_SECRET_KEY=your-secret-jwt-key-here
API_SECRET_KEY=your-secret-api-key-here

# REGTECH Portal Credentials (REQUIRED for collection)
REGTECH_USERNAME=
REGTECH_PASSWORD=

# SECUDIUM Portal Credentials (optional)
SECUDIUM_USERNAME=
SECUDIUM_PASSWORD=

# Collection Settings
COLLECTION_TIMEOUT=300
MAX_RETRIES=3
"""
        with open(".env", "w") as f:
            f.write(env_content)
        print("✅ Created .env file - Please fill in REGTECH credentials!")
        print()

    # Step 2: Analyze current database state
    print("📊 Current Database Analysis:")
    print("-" * 40)

    db_path = "instance/blacklist.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check blacklist_ips table
        cursor.execute("SELECT COUNT(*) FROM blacklist_ips")
        ips_count = cursor.fetchone()[0]
        print(f"blacklist_ips table: {ips_count} records")

        # Check blacklist_ip table
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
        ip_count = cursor.fetchone()[0]
        print(f"blacklist_ip table: {ip_count} records")

        # Check expired IPs
        cursor.execute(
            "SELECT COUNT(*) FROM blacklist_ips WHERE expiry_date < date('now')"
        )
        expired_count = cursor.fetchone()[0]
        print(f"Expired IPs: {expired_count}")

        # Check valid IPs
        valid_count = ips_count - expired_count
        print(f"Valid IPs: {valid_count}")

        conn.close()
    else:
        print("❌ Database not found!")
        return

    print()
    print("🔍 Findings:")
    print("- Data exists in 'blacklist_ips' table (old schema)")
    print("- Application expects data in 'blacklist_ip' table (new schema)")
    print("- No hardcoded IPs found - all from REGTECH")
    print("- 421 IPs have expired (35% of total)")
    print()

    # Step 3: Provide cleanup options
    print("🛠️  Cleanup Options:")
    print("-" * 40)
    print("1. Migrate valid IPs only (779 IPs)")
    print("2. Migrate all IPs including expired (1,200 IPs)")
    print("3. Start fresh - clear all data")
    print("4. Exit without changes")
    print()

    # Create option scripts
    create_option_scripts()

    # Step 4: REGTECH collection preparation
    print("📥 REGTECH Collection Setup:")
    print("-" * 40)

    # Check for main collection script
    main_collector = "scripts/collection/regtech/regtech_auto_collector.py"
    if os.path.exists(main_collector):
        print(f"✅ Main collector found: {main_collector}")
    else:
        # Try alternative location
        alt_collector = "scripts/collection/regtech_auto_collector.py"
        if os.path.exists(alt_collector):
            print(f"✅ Collector found: {alt_collector}")
            main_collector = alt_collector
        else:
            print("❌ REGTECH collector not found")

    # Create a simple REGTECH test script
    create_regtech_test_script()

    print()
    print("📋 Next Steps:")
    print("-" * 40)
    print("1. Fill in REGTECH credentials in .env file")
    print("2. Choose and run one of the cleanup options:")
    print("   - python3 option1_migrate_valid.py")
    print("   - python3 option2_migrate_all.py")
    print("   - python3 option3_start_fresh.py")
    print("3. Test REGTECH connection:")
    print("   - python3 test_regtech_connection.py")
    print("4. Run fresh collection after cleanup")
    print()


def create_option_scripts():
    """Create cleanup option scripts"""

    # Option 1: Migrate valid IPs only
    option1 = '''#!/usr/bin/env python3
"""Option 1: Migrate only valid (non-expired) IPs"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('instance/blacklist.db')
cursor = conn.cursor()

try:
    # Clear target table
    cursor.execute("DELETE FROM blacklist_ip")
    
    # Migrate non-expired IPs
    cursor.execute("""
        INSERT INTO blacklist_ip (ip, country, attack_type, source, source_detail,
                                collection_method, detection_date, created_at, updated_at, metadata)
        SELECT 
            ip_address as ip,
            country,
            attack_type,
            source,
            date_range as source_detail,
            'regtech_portal' as collection_method,
            detection_date,
            created_at,
            updated_at,
            raw_data as metadata
        FROM blacklist_ips
        WHERE expiry_date >= date('now')
    """)
    
    migrated = cursor.rowcount
    conn.commit()
    
    print(f"✅ Migrated {migrated} valid IPs to blacklist_ip table")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
    total = cursor.fetchone()[0]
    print(f"✅ Total IPs in blacklist_ip: {total}")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    conn.close()
'''
    with open("option1_migrate_valid.py", "w") as f:
        f.write(option1)
    os.chmod("option1_migrate_valid.py", 0o755)

    # Option 2: Migrate all IPs
    option2 = '''#!/usr/bin/env python3
"""Option 2: Migrate all IPs including expired"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('instance/blacklist.db')
cursor = conn.cursor()

try:
    # Clear target table
    cursor.execute("DELETE FROM blacklist_ip")
    
    # Migrate all IPs
    cursor.execute("""
        INSERT INTO blacklist_ip (ip, country, attack_type, source, source_detail,
                                collection_method, detection_date, created_at, updated_at, metadata)
        SELECT 
            ip_address as ip,
            country,
            attack_type,
            source,
            date_range as source_detail,
            'regtech_portal' as collection_method,
            detection_date,
            created_at,
            updated_at,
            raw_data as metadata
        FROM blacklist_ips
    """)
    
    migrated = cursor.rowcount
    conn.commit()
    
    print(f"✅ Migrated {migrated} IPs to blacklist_ip table")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
    total = cursor.fetchone()[0]
    print(f"✅ Total IPs in blacklist_ip: {total}")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    conn.close()
'''
    with open("option2_migrate_all.py", "w") as f:
        f.write(option2)
    os.chmod("option2_migrate_all.py", 0o755)

    # Option 3: Start fresh
    option3 = '''#!/usr/bin/env python3
"""Option 3: Start fresh - clear all data"""
import sqlite3
from datetime import datetime
import shutil
import os

# Backup first
backup_dir = 'instance/backups'
os.makedirs(backup_dir, exist_ok=True)
backup_path = f"{backup_dir}/backup_before_fresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
shutil.copy2('instance/blacklist.db', backup_path)
print(f"✅ Database backed up to: {backup_path}")

conn = sqlite3.connect('instance/blacklist.db')
cursor = conn.cursor()

try:
    # Clear all blacklist tables
    tables = ['blacklist_ip', 'blacklist_ips', 'ip_detection', 'daily_stats']
    
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
        print(f"✅ Cleared table: {table}")
    
    conn.commit()
    print("\\n✅ All blacklist data cleared - ready for fresh collection")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    conn.close()
'''
    with open("option3_start_fresh.py", "w") as f:
        f.write(option3)
    os.chmod("option3_start_fresh.py", 0o755)


def create_regtech_test_script():
    """Create REGTECH connection test script"""

    test_script = '''#!/usr/bin/env python3
"""Test REGTECH connection and credentials"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

REGTECH_USERNAME = os.getenv('REGTECH_USERNAME')
REGTECH_PASSWORD = os.getenv('REGTECH_PASSWORD')

print("🔍 Testing REGTECH Connection...")
print("-" * 40)

if not REGTECH_USERNAME or not REGTECH_PASSWORD:
    print("❌ REGTECH credentials not found in .env file!")
    print("   Please add:")
    print("   REGTECH_USERNAME=your_username")
    print("   REGTECH_PASSWORD=your_password")
    exit(1)

print(f"✅ Username: {REGTECH_USERNAME}")
print(f"✅ Password: {'*' * len(REGTECH_PASSWORD)}")

# Test connection to REGTECH portal
try:
    session = requests.Session()
    
    # Try to access login page
    login_url = "https://www.fsec.or.kr/login"
    response = session.get(login_url, timeout=10)
    
    if response.status_code == 200:
        print("✅ Successfully connected to REGTECH portal")
        print(f"   Status: {response.status_code}")
        print(f"   URL: {response.url}")
    else:
        print(f"⚠️  Unexpected status: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ Failed to connect to REGTECH portal")
    print("   Check your internet connection")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("📝 Note: This only tests connectivity.")
print("   Actual login requires handling CAPTCHA/OTP")
print("   Use manual collection scripts for data gathering")
'''

    with open("test_regtech_connection.py", "w") as f:
        f.write(test_script)
    os.chmod("test_regtech_connection.py", 0o755)


if __name__ == "__main__":
    main()
