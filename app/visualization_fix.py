#!/usr/bin/env python3
"""
날짜별 수집 시각화 수정 및 테스트 데이터 생성
"""

import json
import random
from datetime import datetime, timedelta


def create_test_collection_data():
    """테스트용 수집 데이터 생성"""
    # 최근 30일 데이터 생성
    test_data = []
    base_date = datetime.now() - timedelta(days=30)

    for i in range(30):
        date = base_date + timedelta(days=i)

        # 랜덤하게 수집 성공/실패 결정
        if random.random() > 0.2:  # 80% 확률로 수집
            ip_count = random.randint(50, 200)
            test_data.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "status": "success",
                    "ip_count": ip_count,
                    "sources": {
                        "regtech": random.randint(20, 100),
                        "secudium": ip_count - random.randint(20, 100),
                    },
                }
            )
        else:
            test_data.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "status": "failed",
                    "ip_count": 0,
                    "sources": {},
                }
            )

    return test_data


def get_daily_trends():
    """일별 트렌드 데이터 생성"""
    data = create_test_collection_data()

    trends = []
    for item in data:
        trends.append(
            {
                "date": item["date"],
                "total": item["ip_count"],
                "regtech": item["sources"].get("regtech", 0),
                "secudium": item["sources"].get("secudium", 0),
                "status": item["status"],
            }
        )

    return trends


def get_collection_calendar():
    """캘린더용 데이터 생성"""
    data = create_test_collection_data()

    calendar_data = {}
    for item in data:
        calendar_data[item["date"]] = {
            "collected": item["status"] == "success",
            "ip_count": item["ip_count"],
            "sources": item["sources"],
        }

    return calendar_data


def get_collection_stats():
    """수집 통계 생성"""
    data = create_test_collection_data()

    total = len(data)
    successful = len([d for d in data if d["status"] == "success"])
    failed = total - successful
    total_ips = sum(d["ip_count"] for d in data)

    return {
        "total_collections": total,
        "successful_collections": successful,
        "failed_collections": failed,
        "total_ips_collected": total_ips,
        "average_ips_per_collection": total_ips // successful if successful > 0 else 0,
        "success_rate": (successful / total * 100) if total > 0 else 0,
    }


if __name__ == "__main__":
    # 테스트 데이터 생성
    print("📊 날짜별 수집 데이터 생성 중...")

    # 일별 트렌드
    trends = get_daily_trends()
    print(f"\n✅ 일별 트렌드: {len(trends)}일 데이터")
    print("   최근 3일:")
    for trend in trends[-3:]:
        print(f"   - {trend['date']}: {trend['total']} IPs")

    # 캘린더 데이터
    calendar = get_collection_calendar()
    print(f"\n✅ 캘린더 데이터: {len(calendar)}일")

    # 통계
    stats = get_collection_stats()
    print("\n✅ 수집 통계:")
    print(f"   - 총 수집: {stats['total_collections']}회")
    print(f"   - 성공률: {stats['success_rate']:.1f}%")
    print(f"   - 총 IP: {stats['total_ips_collected']}개")

    # JSON 파일로 저장
    output = {"trends": trends, "calendar": calendar, "stats": stats}

    with open("test_collection_data.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n💾 test_collection_data.json 파일로 저장됨")
