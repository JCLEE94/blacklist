"""
Blacklist Management Service - 블랙리스트 관리 전용 마이크로서비스
IP 주소의 저장, 검증, 조회, FortiGate 형식 변환 등을 담당
"""

import asyncio
import ipaddress
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from sqlalchemy import (Boolean, Column, DateTime, Integer, String, Text,
                        create_engine, text)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Blacklist Management Service",
    description="IP 블랙리스트 관리 전용 마이크로서비스",
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

# 데이터베이스 설정
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/blacklist")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 데이터베이스 모델
class BlacklistIP(Base):
    __tablename__ = "blacklist_ips"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(45), index=True, nullable=False)  # IPv6 지원
    source = Column(String(50), nullable=False)
    detection_date = Column(DateTime, nullable=False)
    threat_type = Column(String(50))
    country = Column(String(10))
    is_active = Column(Boolean, default=True)
    expires_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# 테이블 생성
Base.metadata.create_all(bind=engine)


# Pydantic 모델
class IPEntryCreate(BaseModel):
    ip: str
    source: str
    detection_date: str
    threat_type: Optional[str] = None
    country: Optional[str] = None

    @validator("ip")
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")


class IPEntryResponse(BaseModel):
    id: int
    ip: str
    source: str
    detection_date: datetime
    threat_type: Optional[str]
    country: Optional[str]
    is_active: bool
    expires_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class FortiGateEntry(BaseModel):
    name: str
    subnet: str
    comment: str


class SearchRequest(BaseModel):
    ips: List[str]


class SearchResult(BaseModel):
    ip: str
    found: bool
    details: Optional[IPEntryResponse] = None


# 의존성 주입
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BlacklistManager:
    """블랙리스트 관리자"""

    def __init__(self, db: Session):
        self.db = db

    async def add_ip_entry(self, entry: IPEntryCreate) -> IPEntryResponse:
        """IP 항목 추가"""
        try:
            # 중복 확인
            existing = (
                self.db.query(BlacklistIP)
                .filter(BlacklistIP.ip == entry.ip, BlacklistIP.source == entry.source)
                .first()
            )

            if existing:
                # 기존 항목 업데이트
                existing.detection_date = datetime.fromisoformat(entry.detection_date)
                existing.threat_type = entry.threat_type
                existing.country = entry.country
                existing.is_active = True
                existing.updated_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(existing)
                return IPEntryResponse.model_validate(existing)

            # 새 항목 생성
            db_entry = BlacklistIP(
                ip=entry.ip,
                source=entry.source,
                detection_date=datetime.fromisoformat(entry.detection_date),
                threat_type=entry.threat_type,
                country=entry.country,
                expires_date=datetime.utcnow() + timedelta(days=90),  # 3개월 보존
            )

            self.db.add(db_entry)
            self.db.commit()
            self.db.refresh(db_entry)

            return IPEntryResponse.model_validate(db_entry)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add IP entry: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def bulk_insert(self, entries: List[IPEntryCreate]) -> Dict[str, Any]:
        """대량 IP 삽입"""
        success_count = 0
        error_count = 0
        errors = []

        for entry in entries:
            try:
                await self.add_ip_entry(entry)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"IP {entry.ip}: {str(e)}")

        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors[:10],  # 처음 10개 오류만 반환
        }

    async def search_ip(self, ip: str) -> Optional[IPEntryResponse]:
        """IP 검색"""
        try:
            ipaddress.ip_address(ip)  # IP 유효성 검사
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid IP address format")

        entry = (
            self.db.query(BlacklistIP)
            .filter(BlacklistIP.ip == ip, BlacklistIP.is_active == True)
            .first()
        )

        if entry:
            return IPEntryResponse.model_validate(entry)
        return None

    async def search_batch(self, ips: List[str]) -> List[SearchResult]:
        """배치 IP 검색"""
        results = []

        for ip in ips:
            try:
                entry = await self.search_ip(ip)
                results.append(
                    SearchResult(ip=ip, found=entry is not None, details=entry)
                )
            except HTTPException:
                results.append(SearchResult(ip=ip, found=False, details=None))

        return results

    async def get_active_ips(self, limit: int = 10000, offset: int = 0) -> List[str]:
        """활성 IP 목록 조회"""
        entries = (
            self.db.query(BlacklistIP.ip)
            .filter(BlacklistIP.is_active == True)
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [entry.ip for entry in entries]

    async def get_fortigate_format(self) -> List[FortiGateEntry]:
        """FortiGate External Connector 형식 변환"""
        entries = self.db.query(BlacklistIP).filter(BlacklistIP.is_active == True).all()

        fortigate_entries = []
        for i, entry in enumerate(entries, 1):
            fortigate_entries.append(
                FortiGateEntry(
                    name=f"blacklist_ip_{i}",
                    subnet=f"{entry.ip}/32",
                    comment=f"Source: {entry.source}, Type: {entry.threat_type or 'unknown'}",
                )
            )

        return fortigate_entries

    async def cleanup_expired(self) -> int:
        """만료된 IP 정리"""
        expired_count = (
            self.db.query(BlacklistIP)
            .filter(
                BlacklistIP.expires_date < datetime.utcnow(),
                BlacklistIP.is_active == True,
            )
            .update({"is_active": False})
        )

        self.db.commit()
        return expired_count

    async def get_statistics(self) -> Dict[str, Any]:
        """통계 조회"""
        total_ips = self.db.query(BlacklistIP).count()
        active_ips = (
            self.db.query(BlacklistIP).filter(BlacklistIP.is_active == True).count()
        )

        # 소스별 통계
        source_stats = self.db.execute(
            text(
                """
            SELECT source, COUNT(*) as count
            FROM blacklist_ips
            WHERE is_active = true
            GROUP BY source
        """
            )
        ).fetchall()

        # 국가별 통계
        country_stats = self.db.execute(
            text(
                """
            SELECT country, COUNT(*) as count
            FROM blacklist_ips
            WHERE is_active = true AND country IS NOT NULL
            GROUP BY country
            ORDER BY count DESC
            LIMIT 10
        """
            )
        ).fetchall()

        return {
            "total_ips": total_ips,
            "active_ips": active_ips,
            "sources": dict(source_stats),
            "top_countries": dict(country_stats),
        }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "service": "blacklist-service",
        "timestamp": datetime.utcnow(),
    }


@app.post("/api/v1/ips", response_model=IPEntryResponse)
async def add_ip(entry: IPEntryCreate, db: Session = Depends(get_db)):
    """IP 추가"""
    manager = BlacklistManager(db)
    return await manager.add_ip_entry(entry)


@app.post("/api/v1/bulk-insert")
async def bulk_insert_ips(entries: List[IPEntryCreate], db: Session = Depends(get_db)):
    """대량 IP 삽입"""
    manager = BlacklistManager(db)
    result = await manager.bulk_insert(entries)
    return {"status": "success", "data": result}


@app.get("/api/v1/ips/{ip}", response_model=Optional[IPEntryResponse])
async def search_ip(ip: str, db: Session = Depends(get_db)):
    """IP 검색"""
    manager = BlacklistManager(db)
    result = await manager.search_ip(ip)
    if result is None:
        raise HTTPException(status_code=404, detail="IP not found")
    return result


@app.post("/api/v1/search", response_model=List[SearchResult])
async def search_batch(request: SearchRequest, db: Session = Depends(get_db)):
    """배치 IP 검색"""
    manager = BlacklistManager(db)
    return await manager.search_batch(request.ips)


@app.get("/api/v1/active-ips")
async def get_active_ips(
    limit: int = Query(10000, le=50000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """활성 IP 목록 조회"""
    manager = BlacklistManager(db)
    ips = await manager.get_active_ips(limit, offset)
    return {"status": "success", "data": ips, "count": len(ips)}


@app.get("/api/v1/fortigate")
async def get_fortigate_format(db: Session = Depends(get_db)):
    """FortiGate External Connector 형식"""
    manager = BlacklistManager(db)
    entries = await manager.get_fortigate_format()
    return {"status": "success", "data": entries, "count": len(entries)}


@app.get("/api/v1/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """통계 조회"""
    manager = BlacklistManager(db)
    stats = await manager.get_statistics()
    return {"status": "success", "data": stats}


@app.delete("/api/v1/cleanup")
async def cleanup_expired_ips(db: Session = Depends(get_db)):
    """만료된 IP 정리"""
    manager = BlacklistManager(db)
    cleaned_count = await manager.cleanup_expired()
    return {"status": "success", "cleaned_count": cleaned_count}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
