#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect("instance/blacklist.db")
cursor = conn.cursor()

# Check if country data exists
cursor.execute("SELECT country, COUNT(*) as count FROM blacklist_ip WHERE country IS NOT NULL AND country != '' GROUP BY country ORDER BY count DESC LIMIT 10")
countries = cursor.fetchall()
print("=== Top Countries ===")
for country, count in countries:
    print(f"{country}: {count}")

# Check unique sources
cursor.execute("SELECT source, COUNT(*) as count FROM blacklist_ip GROUP BY source")
sources = cursor.fetchall()
print("\n=== Sources ===")
for source, count in sources:
    print(f"{source}: {count}")

# Check detection dates distribution
cursor.execute("SELECT detection_date, COUNT(*) as count FROM blacklist_ip GROUP BY detection_date ORDER BY detection_date DESC LIMIT 10")
dates = cursor.fetchall()
print("\n=== Recent Detection Dates ===")
for date, count in dates:
    print(f"{date}: {count}")

# Check threat_type data
cursor.execute("SELECT threat_type, COUNT(*) as count FROM blacklist_ip WHERE threat_type IS NOT NULL GROUP BY threat_type")
threat_types = cursor.fetchall()
print("\n=== Threat Types ===")
for threat_type, count in threat_types:
    print(f"{threat_type}: {count}")

# Check a sample of IPs to see what data we have
cursor.execute("SELECT * FROM blacklist_ip LIMIT 5")
sample_ips = cursor.fetchall()
print("\n=== Sample IP Data ===")
# Get column names
cursor.execute("PRAGMA table_info(blacklist_ip)")
columns = [col[1] for col in cursor.fetchall()]
print("Columns:", columns)
for ip in sample_ips:
    print(dict(zip(columns, ip)))

conn.close()