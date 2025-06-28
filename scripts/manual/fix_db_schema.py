#\!/usr/bin/env python3
"""
Fix database schema mismatch
"""
import sqlite3
import os

def fix_blacklist_db():
    """Update blacklist.db to match the expected schema"""
    db_path = 'instance/blacklist.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(blacklist_ip)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        print(f"Current columns: {column_names}")
        
        if 'ip' not in column_names and 'ip_address' in column_names:
            print("\nFixing schema: renaming ip_address to ip")
            
            # Create a new table with correct schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blacklist_ip_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip VARCHAR(45) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    attack_type VARCHAR(50),
                    country VARCHAR(100),
                    source VARCHAR(100),
                    extra_data TEXT
                )
            """)
            
            # Copy data from old table
            cursor.execute("""
                INSERT INTO blacklist_ip_new (ip, source, created_at)
                SELECT ip_address, source, added_date FROM blacklist_ip
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE blacklist_ip")
            cursor.execute("ALTER TABLE blacklist_ip_new RENAME TO blacklist_ip")
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist_ip(ip)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist_ip(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_created_at ON blacklist_ip(created_at)")
            
            conn.commit()
            print("Schema fixed successfully\!")
            
            # Verify new schema
            cursor.execute("PRAGMA table_info(blacklist_ip)")
            columns = cursor.fetchall()
            print(f"\nNew schema:")
            for col in columns:
                print(f"  {col[1]} {col[2]}")
        else:
            print("Schema already correct or has different issue")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_blacklist_db()
EOF < /dev/null
