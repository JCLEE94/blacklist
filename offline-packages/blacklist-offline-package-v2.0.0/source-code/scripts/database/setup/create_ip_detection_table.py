#!/usr/bin/env python3
"""
Create the missing ip_detection table in blacklist.db
"""
import os
import sqlite3


def create_ip_detection_table():
    """Create the ip_detection table"""
    db_path = "instance/blacklist.db"

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if table already exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ip_detection'"
        )
        if cursor.fetchone():
            print("ip_detection table already exists")
            return

        # Create ip_detection table
        cursor.execute(
            """
            CREATE TABLE ip_detection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip VARCHAR(45) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source VARCHAR(100),
                attack_type VARCHAR(100),
                confidence_score REAL DEFAULT 1.0,
                FOREIGN KEY (ip) REFERENCES blacklist_ip(ip)
            )
        """
        )

        # Create indexes for performance
        cursor.execute("CREATE INDEX idx_ip_detection_ip ON ip_detection(ip)")
        cursor.execute(
            "CREATE INDEX idx_ip_detection_created_at ON ip_detection(created_at)"
        )
        cursor.execute("CREATE INDEX idx_ip_detection_source ON ip_detection(source)")

        conn.commit()
        print("ip_detection table created successfully!")

        # Verify table structure
        cursor.execute("PRAGMA table_info(ip_detection)")
        columns = cursor.fetchall()
        print("\nTable structure:")
        for col in columns:
            print(f"  {col[1]} {col[2]}")

    except Exception as e:
        print(f"Error creating table: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    create_ip_detection_table()
