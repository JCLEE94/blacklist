#!/usr/bin/env python3
"""
간단한 데이터 업데이터 - 파일 기반 데이터 자동 새로고침
"""
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("updater.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class DataUpdater:
    """데이터 새로고침 서비스"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.blacklist_dir = self.data_dir / "blacklist"
        self.current_month = datetime.now().strftime("%Y-%m")

    def update_current_data(self):
        """현재 월 데이터를 전체 IP 목록으로 복사"""
        try:
            # 현재 월 데이터 파일
            current_month_file = (
                self.blacklist_dir
                / "by_detection_month"
                / self.current_month
                / "ips.txt"
            )

            if not current_month_file.exists():
                logger.warning(f"Current month data not found: {current_month_file}")
                return False

            # 전체 IP 목록 파일로 복사
            all_ips_file = self.blacklist_dir / "all_ips.txt"

            logger.info(f"Updating {all_ips_file} from {current_month_file}")
            shutil.copy2(current_month_file, all_ips_file)

            # 통계 업데이트
            self.update_stats()

            logger.info("Data update completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to update data: {e}")
            return False

    def update_stats(self):
        """통계 파일 업데이트"""
        try:
            stats_file = self.data_dir / "stats.json"
            all_ips_file = self.blacklist_dir / "all_ips.txt"

            if all_ips_file.exists():
                with open(all_ips_file, "r") as f:
                    ip_count = sum(
                        1 for line in f if line.strip() and not line.startswith("#")
                    )

                stats = {
                    "last_update": datetime.now().isoformat(),
                    "current_ips": ip_count,
                    "source": "File-based update",
                    "version": "2.0",
                }

                import json

                with open(stats_file, "w") as f:
                    json.dump(stats, f, indent=2)

                logger.info(f"Stats updated: {ip_count} IPs")

        except Exception as e:
            logger.error(f"Failed to update stats: {e}")

    def run_once(self):
        """1회 업데이트 실행"""
        logger.info("Running single data update...")
        return self.update_current_data()

    def run_continuous(self, interval_hours: int = 1):
        """지속적인 업데이트 실행"""
        logger.info(f"Starting continuous updates every {interval_hours} hour(s)")

        while True:
            try:
                self.update_current_data()
                logger.info(f"Next update in {interval_hours} hour(s)")
                time.sleep(interval_hours * 3600)

            except KeyboardInterrupt:
                logger.info("Update service stopped by user")
                break
            except Exception as e:
                logger.error(f"Update service error: {e}")
                time.sleep(300)  # 5분 후 재시도


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="Secudium Data Updater")
    parser.add_argument("--once", action="store_true", help="Run update once and exit")
    parser.add_argument(
        "--interval", type=int, default=1, help="Update interval in hours (default: 1)"
    )
    parser.add_argument(
        "--data-dir", default="data", help="Data directory path (default: data)"
    )

    args = parser.parse_args()

    updater = DataUpdater(args.data_dir)

    if args.once:
        success = updater.run_once()
        sys.exit(0 if success else 1)
    else:
        updater.run_continuous(args.interval)


if __name__ == "__main__":
    main()
