#!/usr/bin/env python3
"""Check data loading directly"""
import os
from pathlib import Path

# Check directory structure
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, 'data')
blacklist_dir = os.path.join(data_dir, 'blacklist')
detection_dir = os.path.join(blacklist_dir, 'by_detection_month')

print(f"Base directory: {base_dir}")
print(f"Data directory: {data_dir}")
print(f"Blacklist directory: {blacklist_dir}")
print(f"Detection directory: {detection_dir}")
print()

# Check if directories exist
print(f"Data dir exists: {os.path.exists(data_dir)}")
print(f"Blacklist dir exists: {os.path.exists(blacklist_dir)}")
print(f"Detection dir exists: {os.path.exists(detection_dir)}")
print()

# List month directories
if os.path.exists(detection_dir):
    print("Month directories:")
    for month_dir in sorted(Path(detection_dir).glob("*/")):
        if month_dir.is_dir():
            ips_file = month_dir / "ips.txt"
            if ips_file.exists():
                with open(ips_file, 'r') as f:
                    count = sum(1 for line in f if line.strip())
                print(f"  - {month_dir.name}: {count} IPs")
            else:
                print(f"  - {month_dir.name}: No ips.txt file")
                
# Check all_ips.txt
all_ips_file = os.path.join(blacklist_dir, 'all_ips.txt')
if os.path.exists(all_ips_file):
    with open(all_ips_file, 'r') as f:
        count = sum(1 for line in f if line.strip())
    print(f"\nall_ips.txt: {count} IPs")