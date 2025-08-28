#!/usr/bin/env python3
"""
Timezone Utilities for KST Migration
Korean Standard Time (Asia/Seoul) 시간대 처리 유틸리티
"""

from datetime import datetime, timezone
from typing import Optional, Union
import pytz


# KST 타임존 설정
KST = pytz.timezone("Asia/Seoul")
UTC = pytz.UTC


def get_kst_now() -> datetime:
    """현재 KST 시간 반환"""
    return datetime.now(KST)


def get_utc_now() -> datetime:
    """현재 UTC 시간 반환"""
    return datetime.now(UTC)


def utc_to_kst(dt: datetime) -> datetime:
    """UTC 시간을 KST로 변환"""
    if dt.tzinfo is None:
        # naive datetime을 UTC로 가정
        dt = UTC.localize(dt)
    elif dt.tzinfo != UTC:
        # 다른 시간대를 UTC로 변환 후 KST로 변환
        dt = dt.astimezone(UTC)

    return dt.astimezone(KST)


def kst_to_utc(dt: datetime) -> datetime:
    """KST 시간을 UTC로 변환"""
    if dt.tzinfo is None:
        # naive datetime을 KST로 가정
        dt = KST.localize(dt)
    elif dt.tzinfo != KST:
        # 다른 시간대를 KST로 변환 후 UTC로 변환
        dt = dt.astimezone(KST)

    return dt.astimezone(UTC)


def format_kst_timestamp(dt: Optional[datetime] = None) -> str:
    """KST 시간을 한국 형식으로 포맷팅"""
    if dt is None:
        dt = get_kst_now()

    if dt.tzinfo is None:
        dt = KST.localize(dt)
    else:
        dt = dt.astimezone(KST)

    return dt.strftime("%Y-%m-%d %H:%M:%S KST")


def format_iso_kst(dt: Optional[datetime] = None) -> str:
    """KST 시간을 ISO 형식으로 포맷팅"""
    if dt is None:
        dt = get_kst_now()

    if dt.tzinfo is None:
        dt = KST.localize(dt)
    else:
        dt = dt.astimezone(KST)

    return dt.isoformat()


def parse_kst_string(time_str: str) -> datetime:
    """KST 시간 문자열을 datetime 객체로 파싱"""
    # 다양한 형식 지원
    formats = [
        "%Y-%m-%d %H:%M:%S KST",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S+09:00",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(
                time_str.replace(" KST", ""), fmt.replace(" KST", "")
            )
            return KST.localize(dt)
        except ValueError:
            continue

    raise ValueError(f"시간 형식을 파싱할 수 없습니다: {time_str}")


def get_timezone_info() -> dict:
    """현재 시간대 정보 반환"""
    now_kst = get_kst_now()
    now_utc = get_utc_now()

    return {
        "kst_time": format_kst_timestamp(now_kst),
        "utc_time": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "kst_iso": format_iso_kst(now_kst),
        "utc_iso": now_utc.isoformat(),
        "offset": "+09:00",
        "timezone_name": "Asia/Seoul",
    }


def migrate_datetime_field(value: Union[str, datetime, None]) -> Optional[datetime]:
    """기존 datetime 필드를 KST로 마이그레이션"""
    if value is None:
        return None

    if isinstance(value, str):
        try:
            # ISO 형식 파싱 시도
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                # naive datetime을 UTC로 가정
                dt = UTC.localize(dt)
            return dt.astimezone(KST)
        except ValueError:
            # 문자열 파싱 시도
            return parse_kst_string(value)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            # naive datetime을 UTC로 가정하고 KST로 변환
            return UTC.localize(value).astimezone(KST)
        else:
            # 시간대 정보가 있는 경우 KST로 변환
            return value.astimezone(KST)

    return value


# Backward compatibility aliases
def datetime_now_kst():
    """기존 코드 호환성을 위한 별칭"""
    return get_kst_now()


def datetime_utc_to_kst(dt):
    """기존 코드 호환성을 위한 별칭"""
    return utc_to_kst(dt)


if __name__ == "__main__":
    # 테스트 및 데모
    print("🕐 Timezone Utils Test")
    print("=" * 50)

    info = get_timezone_info()
    for key, value in info.items():
        print(f"{key}: {value}")

    print("\n🔄 변환 테스트:")
    utc_time = get_utc_now()
    kst_time = utc_to_kst(utc_time)
    print(f"UTC: {utc_time}")
    print(f"KST: {kst_time}")
    print(f"Formatted: {format_kst_timestamp(kst_time)}")

    print("\n✅ Timezone Utils 테스트 완료")
