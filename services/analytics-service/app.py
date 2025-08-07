"""
Analytics Service - 분석 및 통계 전용 마이크로서비스
블랙리스트 데이터의 트렌드 분석, 통계 생성, 리포팅 기능을 담당
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime, timedelta
import httpx
import pandas as pd
import numpy as np
from collections import defaultdict
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Analytics Service", description="블랙리스트 분석 및 통계 전용 마이크로서비스", version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 데이터 모델
class TrendRequest(BaseModel):
    period: str = "7d"  # 7d, 30d, 90d
    granularity: str = "daily"  # hourly, daily, weekly


class TrendData(BaseModel):
    date: str
    count: int
    source_breakdown: Dict[str, int]


class GeographicData(BaseModel):
    country: str
    count: int
    percentage: float


class ThreatTypeData(BaseModel):
    threat_type: str
    count: int
    percentage: float


class AnalyticsReport(BaseModel):
    period: str
    total_ips: int
    new_ips: int
    growth_rate: float
    trends: List[TrendData]
    geographic_distribution: List[GeographicData]
    threat_types: List[ThreatTypeData]
    top_sources: Dict[str, int]


class AnalyticsManager:
    """분석 관리자"""

    def __init__(self):
        self.blacklist_service_url = os.getenv(
            "BLACKLIST_SERVICE_URL", "http://blacklist-service:8001"
        )
        # 캐시된 데이터 (실제로는 Redis 사용)
        self.cache = {}
        self.cache_ttl = 300  # 5분

    async def _get_blacklist_data(self) -> List[Dict]:
        """블랙리스트 서비스에서 데이터 조회"""
        cache_key = "blacklist_data"
        now = datetime.utcnow()

        # 캐시 확인
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (now - cached_time).seconds < self.cache_ttl:
                return cached_data

        async with httpx.AsyncClient() as client:
            try:
                # 통계 데이터 조회
                stats_response = await client.get(
                    f"{self.blacklist_service_url}/api/v1/statistics"
                )
                stats_response.raise_for_status()
                stats_data = stats_response.json()

                # 활성 IP 데이터 조회 (샘플링)
                ips_response = await client.get(
                    f"{self.blacklist_service_url}/api/v1/active-ips?limit=1000"
                )
                ips_response.raise_for_status()
                ips_data = ips_response.json()

                combined_data = {
                    "statistics": stats_data["data"],
                    "sample_ips": ips_data["data"],
                }

                # 캐시에 저장
                self.cache[cache_key] = (combined_data, now)
                return combined_data

            except Exception as e:
                logger.error(f"Failed to fetch blacklist data: {e}")
                raise HTTPException(
                    status_code=503, detail="Blacklist service unavailable"
                )

    async def generate_trend_analysis(
        self, period: str = "7d", granularity: str = "daily"
    ) -> List[TrendData]:
        """트렌드 분석 생성"""
        # 실제 구현에서는 시계열 데이터베이스에서 조회
        # 여기서는 시뮬레이션 데이터 생성

        days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 7)
        trends = []

        base_date = datetime.utcnow() - timedelta(days=days)

        for i in range(days):
            date = base_date + timedelta(days=i)

            # 시뮬레이션 데이터 생성 (실제로는 DB 쿼리)
            base_count = 1000 + np.random.randint(-100, 200)
            regtech_count = int(base_count * 0.7)
            secudium_count = base_count - regtech_count

            trends.append(
                TrendData(
                    date=date.strftime("%Y-%m-%d"),
                    count=base_count,
                    source_breakdown={
                        "regtech": regtech_count,
                        "secudium": secudium_count,
                    },
                )
            )

        return trends

    async def generate_geographic_distribution(self) -> List[GeographicData]:
        """지리적 분포 분석"""
        data = await self._get_blacklist_data()
        stats = data["statistics"]

        # 국가별 통계가 있다면 사용, 없으면 시뮬레이션
        if "top_countries" in stats:
            country_data = stats["top_countries"]
            total = sum(country_data.values())

            return [
                GeographicData(
                    country=country,
                    count=count,
                    percentage=round((count / total) * 100, 2),
                )
                for country, count in country_data.items()
            ]
        else:
            # 시뮬레이션 데이터
            countries = ["KR", "US", "CN", "RU", "JP", "DE", "BR", "IN"]
            total = 10000
            geo_data = []

            for country in countries:
                count = np.random.randint(100, 2000)
                geo_data.append(
                    GeographicData(
                        country=country,
                        count=count,
                        percentage=round((count / total) * 100, 2),
                    )
                )

            return sorted(geo_data, key=lambda x: x.count, reverse=True)

    async def generate_threat_type_analysis(self) -> List[ThreatTypeData]:
        """위협 유형 분석"""
        # 시뮬레이션 데이터 (실제로는 DB에서 위협 유형별 집계)
        threat_types = {
            "malicious": 4500,
            "suspicious": 3200,
            "botnet": 1800,
            "spam": 1200,
            "phishing": 800,
            "unknown": 500,
        }

        total = sum(threat_types.values())

        return [
            ThreatTypeData(
                threat_type=threat_type,
                count=count,
                percentage=round((count / total) * 100, 2),
            )
            for threat_type, count in threat_types.items()
        ]

    async def generate_comprehensive_report(
        self, period: str = "30d"
    ) -> AnalyticsReport:
        """종합 분석 리포트 생성"""
        # 병렬로 각종 분석 수행
        trends_task = self.generate_trend_analysis(period)
        geo_task = self.generate_geographic_distribution()
        threat_task = self.generate_threat_type_analysis()

        trends, geo_dist, threat_types = await asyncio.gather(
            trends_task, geo_task, threat_task
        )

        # 블랙리스트 데이터 조회
        data = await self._get_blacklist_data()
        stats = data["statistics"]

        # 성장률 계산
        current_total = stats.get("active_ips", 0)
        previous_total = current_total * 0.95  # 시뮬레이션
        growth_rate = round(
            ((current_total - previous_total) / previous_total) * 100, 2
        )

        return AnalyticsReport(
            period=period,
            total_ips=current_total,
            new_ips=int(current_total - previous_total),
            growth_rate=growth_rate,
            trends=trends,
            geographic_distribution=geo_dist,
            threat_types=threat_types,
            top_sources=stats.get("sources", {}),
        )

    async def generate_realtime_metrics(self) -> Dict[str, Any]:
        """실시간 메트릭 생성"""
        data = await self._get_blacklist_data()
        stats = data["statistics"]

        # 실시간 메트릭 계산
        current_hour = datetime.utcnow().hour
        hourly_activity = np.random.randint(50, 200, 24).tolist()

        return {
            "active_ips": stats.get("active_ips", 0),
            "total_sources": len(stats.get("sources", {})),
            "hourly_activity": hourly_activity,
            "current_hour_activity": hourly_activity[current_hour],
            "avg_daily_growth": np.random.randint(50, 150),
            "detection_rate": round(np.random.uniform(85, 95), 1),
            "last_updated": datetime.utcnow().isoformat(),
        }


# 서비스 인스턴스
analytics_manager = AnalyticsManager()


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "service": "analytics-service",
        "timestamp": datetime.utcnow(),
    }


@app.get("/api/v1/trends", response_model=List[TrendData])
async def get_trends(
    period: str = Query("7d", regex="^(7d|30d|90d)$"),
    granularity: str = Query("daily", regex="^(hourly|daily|weekly)$"),
):
    """트렌드 분석 조회"""
    trends = await analytics_manager.generate_trend_analysis(period, granularity)
    return trends


@app.get("/api/v1/geographic", response_model=List[GeographicData])
async def get_geographic_distribution():
    """지리적 분포 분석"""
    geo_data = await analytics_manager.generate_geographic_distribution()
    return geo_data


@app.get("/api/v1/threat-types", response_model=List[ThreatTypeData])
async def get_threat_types():
    """위협 유형 분석"""
    threat_data = await analytics_manager.generate_threat_type_analysis()
    return threat_data


@app.get("/api/v1/report", response_model=AnalyticsReport)
async def get_comprehensive_report(period: str = Query("30d", regex="^(7d|30d|90d)$")):
    """종합 분석 리포트"""
    report = await analytics_manager.generate_comprehensive_report(period)
    return report


@app.get("/api/v1/realtime")
async def get_realtime_metrics():
    """실시간 메트릭"""
    metrics = await analytics_manager.generate_realtime_metrics()
    return {"status": "success", "data": metrics}


@app.get("/api/v1/performance")
async def get_performance_metrics():
    """성능 메트릭"""
    # 각 서비스의 응답 시간 측정
    start_time = datetime.utcnow()

    try:
        await analytics_manager._get_blacklist_data()
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return {
            "status": "success",
            "data": {
                "blacklist_service_response_time_ms": round(response_time, 2),
                "analytics_processing_time_ms": round(np.random.uniform(10, 50), 2),
                "cache_hit_rate": round(np.random.uniform(70, 95), 1),
                "memory_usage_mb": round(np.random.uniform(100, 300), 1),
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "blacklist_service_available": False,
        }


if __name__ == "__main__":
    import uvicorn
    import os

    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("SERVICE_PORT", "8002"))
    uvicorn.run(app, host=host, port=port)
