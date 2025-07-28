#!/usr/bin/env python3
"""
Migrate blacklist.db to match expected schema
"""
import os
import sqlite3


def migrate_blacklist_db():
    """Migrate blacklist.db to use 'ip' column instead of 'ip_address'"""
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
            print("\nMigrating schema...")

            # Create new table with correct schema
            cursor.execute(
                """
                CREATE TABLE blacklist_ip_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip VARCHAR(45) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    attack_type VARCHAR(50),
                    country VARCHAR(100),
                    source VARCHAR(100),
                    extra_data TEXT
                )
            """
            )

            # Copy existing data
            cursor.execute(
                """
                INSERT INTO blacklist_ip_new (ip, source, created_at)
                SELECT ip_address, source, added_date
                FROM blacklist_ip
            """
            )

            # Drop old table
            cursor.execute("DROP TABLE blacklist_ip")

            # Rename new table
            cursor.execute("ALTER TABLE blacklist_ip_new RENAME TO blacklist_ip")

            # Create indexes
            cursor.execute("CREATE INDEX idx_blacklist_ip ON blacklist_ip(ip)")
            cursor.execute("CREATE INDEX idx_blacklist_source ON blacklist_ip(source)")
            cursor.execute(
                "CREATE INDEX idx_blacklist_created_at ON blacklist_ip(created_at)"
            )

            conn.commit()
            print("Migration completed successfully!")

            # Verify
            cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
            count = cursor.fetchone()[0]
            print(f"Migrated {count} records")

        elif 'ip' in column_names:
            print("Schema already correct!")
        else:
            print("Unknown schema format")

    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_blacklist_db()
