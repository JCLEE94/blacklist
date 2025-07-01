#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('instance/blacklist.db')
cursor = conn.cursor()

print("Table structure for blacklist_ip:")
cursor.execute("PRAGMA table_info(blacklist_ip)")
for col in cursor.fetchall():
    print(f"  {col}")

conn.close()