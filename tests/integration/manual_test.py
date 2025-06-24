#!/usr/bin/env python3
"""Manual test of blacklist manager"""
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['BLACKLIST_USERNAME'] = 'nextrade'
os.environ['BLACKLIST_PASSWORD'] = 'Sprtmxm1@3'
os.environ['FLASK_ENV'] = 'development'

# Import after setting env vars
from core.blacklist_manager import IntegratedBlacklistManager
from utils.cache import CacheService

# Initialize with absolute path
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
print(f"Using data directory: {data_dir}")

# Create cache service
cache = CacheService()

# Create manager
manager = IntegratedBlacklistManager(
    data_dir=data_dir,
    cache_backend=cache,
    cache_ttl=300
)

print(f"\nBlacklist directory: {manager.blacklist_dir}")
print(f"Detection directory: {manager.detection_dir}")

# Test loading
print("\nTesting data loading...")

# Get available months
months = manager.get_available_months()
print(f"Available months: {len(months)}")
for month in months:
    print(f"  - {month}")

# Get active IPs
active_ips, active_months = manager.get_active_ips()
print(f"\nActive IPs: {len(active_ips)}")
print(f"Active months: {active_months}")

# Test API output format
print("\nSample IPs (first 10):")
for i, ip in enumerate(sorted(active_ips)[:10], 1):
    print(f"{ip}")