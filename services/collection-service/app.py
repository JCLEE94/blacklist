"""
Collection Service - 데이터 수집 전용 마이크로서비스
REGTECH, SECUDIUM 등의 외부 소스에서 IP 데이터를 수집하는 서비스
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Collection Service",
    description="IP 블랙리스트 데이터 수집 전용 마이크로서비스",
    version="1.0.0",
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
class CollectionRequest(BaseModel):
    source: str  # "regtech", "secudium"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    force: bool = False


class CollectionResult(BaseModel):
    success: bool
    message: str
    collected_count: int
    source: str
    timestamp: datetime


class IPEntry(BaseModel):
    ip: str
    source: str
    detection_date: str
    threat_type: Optional[str] = None
    country: Optional[str] = None


# 수집 상태 저장소 (실제로는 Redis 등 사용)
collection_status: Dict[str, Any] = {
    "regtech": {"enabled": True, "last_run": None, "status": "idle"},
    "secudium": {"enabled": False, "last_run": None, "status": "idle"},
}

# 수집된 데이터 임시 저장소 (실제로는 메시지 큐 사용)
collected_data: List[IPEntry] = []


class CollectionManager:
    """데이터 수집 관리자"""

    def __init__(self):
        self.collectors = {
            "regtech": RegtechCollector(),
            "secudium": SecudiumCollector(),
        }

    async def collect_data(
        self, source: str, start_date: str = None, end_date: str = None
    ) -> CollectionResult:
        """지정된 소스에서 데이터 수집"""
        if source not in self.collectors:
            raise ValueError(f"Unknown source: {source}")

        if not collection_status[source]["enabled"]:
            raise ValueError(f"Collection disabled for source: {source}")

        collection_status[source]["status"] = "running"
        collection_status[source]["last_run"] = datetime.now()

        try:
            collector = self.collectors[source]
            entries = await collector.collect(start_date, end_date)

            # 수집된 데이터를 임시 저장소에 추가
            collected_data.extend(entries)

            # 실제 구현에서는 메시지 큐로 전송
            await self._send_to_blacklist_service(entries)

            collection_status[source]["status"] = "completed"

            return CollectionResult(
                success=True,
                message=f"Successfully collected {len(entries)} IPs from {source}",
                collected_count=len(entries),
                source=source,
                timestamp=datetime.now(),
            )

        except Exception as e:
            collection_status[source]["status"] = "error"
            logger.error(f"Collection failed for {source}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _send_to_blacklist_service(self, entries: List[IPEntry]):
        """블랙리스트 관리 서비스로 데이터 전송"""
        blacklist_service_url = os.getenv(
            "BLACKLIST_SERVICE_URL", "http://blacklist-service:8001"
        )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{blacklist_service_url}/api/v1/bulk-insert",
                    json=[entry.dict() for entry in entries],
                    timeout=30,
                )
                response.raise_for_status()
                logger.info(f"Sent {len(entries)} entries to blacklist service")
            except Exception as e:
                logger.error(f"Failed to send data to blacklist service: {e}")
                # 실제 구현에서는 재시도 로직 추가


class RegtechCollector:
    """REGTECH 데이터 수집기"""

    async def collect(
        self, start_date: str = None, end_date: str = None
    ) -> List[IPEntry]:
        """REGTECH에서 데이터 수집"""
        # 기존 REGTECH 수집 로직을 비동기로 변환
        logger.info(f"Starting REGTECH collection from {start_date} to {end_date}")

        # 실제 구현에서는 기존 RegtechCollector 로직 사용
        await asyncio.sleep(2)  # 시뮬레이션

        # 샘플 데이터 반환
        return [
            IPEntry(
                ip=f"192.168.{i}.{j}",
                source="regtech",
                detection_date=datetime.now().strftime("%Y-%m-%d"),
                threat_type="malicious",
                country="KR",
            )
            for i in range(1, 5)
            for j in range(1, 10)
        ]


class SecudiumCollector:
    """SECUDIUM 데이터 수집기"""

    async def collect(
        self, start_date: str = None, end_date: str = None
    ) -> List[IPEntry]:
        """SECUDIUM에서 데이터 수집"""
        logger.info(f"Starting SECUDIUM collection from {start_date} to {end_date}")

        # 실제 구현에서는 기존 SecudiumCollector 로직 사용
        await asyncio.sleep(1)  # 시뮬레이션

        return [
            IPEntry(
                ip=f"10.0.{i}.{j}",
                source="secudium",
                detection_date=datetime.now().strftime("%Y-%m-%d"),
                threat_type="suspicious",
                country="US",
            )
            for i in range(1, 3)
            for j in range(1, 5)
        ]


# 서비스 인스턴스
collection_manager = CollectionManager()


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "service": "collection-service",
        "timestamp": datetime.now(),
        "sources": collection_status,
    }


@app.get("/api/v1/status")
async def get_collection_status():
    """수집 상태 조회"""
    return {
        "status": "success",
        "data": collection_status,
        "total_collected": len(collected_data),
    }


@app.post("/api/v1/collect")
async def trigger_collection(
    request: CollectionRequest, background_tasks: BackgroundTasks
):
    """데이터 수집 트리거"""
    try:
        # 백그라운드에서 수집 실행
        background_tasks.add_task(
            collection_manager.collect_data,
            request.source,
            request.start_date,
            request.end_date,
        )

        return {
            "status": "success",
            "message": f"Collection started for {request.source}",
            "timestamp": datetime.now(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/sources/{source}/enable")
async def enable_source(source: str):
    """데이터 소스 활성화"""
    if source not in collection_status:
        raise HTTPException(status_code=404, detail=f"Source {source} not found")

    collection_status[source]["enabled"] = True
    return {"status": "success", "message": f"Source {source} enabled"}


@app.put("/api/v1/sources/{source}/disable")
async def disable_source(source: str):
    """데이터 소스 비활성화"""
    if source not in collection_status:
        raise HTTPException(status_code=404, detail=f"Source {source} not found")

    collection_status[source]["enabled"] = False
    return {"status": "success", "message": f"Source {source} disabled"}


@app.get("/api/v1/collected-data")
async def get_collected_data(limit: int = 100):
    """수집된 데이터 조회 (디버깅용)"""
    return {
        "status": "success",
        "data": collected_data[-limit:],
        "total": len(collected_data),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
