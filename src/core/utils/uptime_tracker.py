"""
시스템 업타임 추적 유틸리티
애플리케이션 시작 시간을 기록하고 실시간 업타임을 계산
"""

import os
import time
import logging
from datetime import datetime, timedelta
from functools import lru_cache

logger = logging.getLogger(__name__)

# 전역 시작 시간 (모듈 로드 시점에 기록)
_START_TIME = time.time()
_START_DATETIME = datetime.now()


def get_start_time():
    """애플리케이션 시작 시간 반환"""
    return _START_TIME


def get_start_datetime():
    """애플리케이션 시작 날짜시간 반환"""
    return _START_DATETIME


def get_uptime_seconds():
    """현재 업타임을 초 단위로 반환"""
    return time.time() - _START_TIME


def get_uptime_formatted():
    """업타임을 읽기 쉬운 형식으로 반환

    Returns:
        str: "2일 3시간 45분 12초" 형식
    """
    total_seconds = int(get_uptime_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}일")
    if hours > 0:
        parts.append(f"{hours}시간")
    if minutes > 0:
        parts.append(f"{minutes}분")
    if seconds > 0 or not parts:  # 시작한지 1분 미만인 경우도 초를 표시
        parts.append(f"{seconds}초")

    return " ".join(parts)


def get_uptime_english():
    """업타임을 영어 형식으로 반환

    Returns:
        str: "2d 3h 45m 12s" 형식
    """
    total_seconds = int(get_uptime_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def get_uptime_detailed():
    """상세한 업타임 정보 반환

    Returns:
        dict: 업타임 관련 모든 정보
    """
    uptime_seconds = get_uptime_seconds()
    start_time = get_start_datetime()

    return {
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_formatted": get_uptime_formatted(),
        "uptime_english": get_uptime_english(),
        "started_at": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "started_at_iso": start_time.isoformat(),
        "started_at_timestamp": _START_TIME,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "KST" if "Asia/Seoul" in str(start_time.astimezone()) else "UTC",
    }


def get_system_load_average():
    """시스템 로드 평균 반환 (Unix 시스템만)"""
    try:
        if hasattr(os, "getloadavg"):
            load1, load5, load15 = os.getloadavg()
            return {
                "load_1min": round(load1, 2),
                "load_5min": round(load5, 2),
                "load_15min": round(load15, 2),
            }
    except:
        pass
    return None


def get_memory_usage():
    """메모리 사용량 반환"""
    try:
        import psutil

        memory = psutil.virtual_memory()
        return {
            "total_mb": round(memory.total / 1024 / 1024, 1),
            "available_mb": round(memory.available / 1024 / 1024, 1),
            "used_mb": round(memory.used / 1024 / 1024, 1),
            "percent": round(memory.percent, 1),
        }
    except ImportError:
        return None


def get_system_uptime_info():
    """시스템 전체 정보와 애플리케이션 업타임 결합"""
    app_uptime = get_uptime_detailed()

    # 시스템 정보 추가 시도
    system_info = {
        "load_average": get_system_load_average(),
        "memory_usage": get_memory_usage(),
    }

    # OS 업타임 시도 (Linux)
    try:
        with open("/proc/uptime", "r") as f:
            os_uptime_seconds = float(f.readline().split()[0])
            os_uptime_days = int(os_uptime_seconds // 86400)
            os_uptime_hours = int((os_uptime_seconds % 86400) // 3600)
            system_info["os_uptime"] = f"{os_uptime_days}일 {os_uptime_hours}시간"
    except:
        system_info["os_uptime"] = None

    return {"application": app_uptime, "system": system_info}


# 업타임 상태를 문자열로 평가
def get_uptime_status():
    """업타임 기간에 따른 상태 반환"""
    seconds = get_uptime_seconds()

    if seconds < 60:  # 1분 미만
        return "starting"
    elif seconds < 3600:  # 1시간 미만
        return "running"
    elif seconds < 86400:  # 1일 미만
        return "stable"
    elif seconds < 604800:  # 1주 미만
        return "mature"
    else:  # 1주 이상
        return "veteran"


# 로거에 시작 정보 기록
logger.info(
    f"Uptime tracker initialized. Started at: {_START_DATETIME.strftime('%Y-%m-%d %H:%M:%S')}"
)
