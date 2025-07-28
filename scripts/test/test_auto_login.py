#!/usr/bin/env python3
"""
Test auto-login functionality for REGTECH collector
"""

import logging

from src.core.regtech_collector import RegtechCollector

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_auto_login():
    """Test the auto-login functionality"""
    print("\n🧪 Testing REGTECH Auto-Login Functionality")
    print("=" * 60)

    # Create collector
    collector = RegtechCollector('data')

    # Test with small date range to minimize data
    start_date = "20250116"
    end_date = "20250116"

    print(f"\n📅 Testing collection for date: {start_date}")
    print("🔄 If cookies are expired, auto-login will be triggered...")

    try:
        # Attempt collection
        ips = collector.collect_from_web(
            start_date=start_date, end_date=end_date, max_pages=1
        )

        if ips:
            print(f"\n✅ Collection successful!")
            print(f"📊 Collected {len(ips)} IPs")

            # Show first few IPs
            print("\n🔍 Sample IPs collected:")
            for i, ip in enumerate(ips[:3]):
                print(f"  {i+1}. {ip.ip_address} ({ip.country}) - {ip.reason}")
        else:
            print(
                "\n⚠️  No IPs collected (this could be normal if no data for this date)"
            )

    except Exception as e:
        print(f"\n❌ Error during collection: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Test completed")


if __name__ == "__main__":
    test_auto_login()
