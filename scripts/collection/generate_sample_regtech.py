#!/usr/bin/env python3
"""
Generate sample REGTECH data for testing (100+ IPs)
"""
import random
import sqlite3
from datetime import datetime, timedelta


def generate_sample_ips():
    """Generate 100+ sample IPs with realistic data"""
    ips = []

    # Generate IPs from known malicious ranges
    ranges = [
        # Russian ranges
        ("185.220.100.", 1, 50),  # Common botnet range
        ("185.220.101.", 1, 30),  # Common botnet range
        # Chinese ranges
        ("223.111.20.", 1, 25),  # Known spam range
        ("117.50.7.", 1, 20),  # Known attack range
        # North Korean ranges
        ("175.45.176.", 1, 15),  # Known APT range
    ]

    attack_types = [
        "DDoS Attack",
        "Brute Force",
        "Port Scan",
        "Web Shell Upload",
        "SQL Injection",
        "Malware Distribution",
        "Phishing",
        "Ransomware",
        "Botnet C&C",
    ]

    countries = {"185.220.": "RU", "223.111.": "CN", "117.50.": "CN", "175.45.": "KP"}

    # Generate IPs
    for prefix, start, count in ranges:
        country = countries.get(prefix[:8], "XX")
        for i in range(start, start + count):
            # Random detection date within last 30 days
            days_ago = random.randint(1, 30)
            detection_date = (datetime.now() - timedelta(days=days_ago)).strftime(
                '%Y-%m-%d'
            )

            ips.append(
                {
                    'ip': f"{prefix}{i}",
                    'country': country,
                    'attack_type': random.choice(attack_types),
                    'detection_date': detection_date,
                    'source': 'REGTECH',
                    'status': 'active',
                }
            )

    # Add some specific known malicious IPs
    known_bad = [
        ("162.55.186.74", "DE", "Botnet C&C"),
        ("45.155.205.68", "NL", "DDoS Attack"),
        ("193.106.31.105", "RO", "Brute Force"),
        ("89.248.165.52", "NL", "Port Scan"),
        ("185.191.32.198", "RU", "Ransomware"),
    ]

    for ip, country, attack in known_bad:
        ips.append(
            {
                'ip': ip,
                'country': country,
                'attack_type': attack,
                'detection_date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'REGTECH',
                'status': 'active',
            }
        )

    return ips


def main():
    print("🔧 Generating sample REGTECH data...")

    # Generate IPs
    sample_ips = generate_sample_ips()
    print(f"📊 Generated {len(sample_ips)} sample IPs")

    # Connect to database
    conn = sqlite3.connect('instance/blacklist.db')
    cursor = conn.cursor()

    # Insert IPs
    inserted = 0
    for ip_data in sample_ips:
        try:
            cursor.execute(
                '''
                INSERT OR IGNORE INTO blacklist_ip 
                (ip, country, attack_type, source, detection_date, source_detail, collection_method)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
                (
                    ip_data['ip'],
                    ip_data['country'],
                    ip_data['attack_type'],
                    ip_data['source'],
                    ip_data['detection_date'],
                    'REGTECH Portal',
                    'sample_generation',
                ),
            )
            if cursor.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"Error inserting {ip_data['ip']}: {e}")

    conn.commit()

    # Verify
    total_count = cursor.execute('SELECT COUNT(*) FROM blacklist_ip').fetchone()[0]
    regtech_count = cursor.execute(
        'SELECT COUNT(*) FROM blacklist_ip WHERE source="REGTECH"'
    ).fetchone()[0]

    print(f"\n✅ Inserted {inserted} new IPs")
    print(f"📊 Total IPs in database: {total_count}")
    print(f"🔍 REGTECH IPs: {regtech_count}")

    # Show sample
    print("\n📋 Sample of inserted IPs:")
    sample = cursor.execute(
        '''
        SELECT ip, country, attack_type, detection_date 
        FROM blacklist_ip 
        WHERE source="REGTECH" 
        ORDER BY detection_date DESC 
        LIMIT 10
    '''
    ).fetchall()

    for ip, country, attack, date in sample:
        print(f"  - {ip} ({country}) - {attack} - {date}")

    conn.close()
    print("\n✅ Sample REGTECH data generation complete!")


if __name__ == '__main__':
    main()
