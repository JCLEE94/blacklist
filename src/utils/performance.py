"""
고급 성능 모니터링 및 최적화 모듈
"""
import asyncio
import functools
import json
import logging
import os
import sqlite3
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import psutil

try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    import json as orjson

    HAS_ORJSON = False

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """성능 메트릭 데이터 클래스"""

    name: str
    duration: float
    timestamp: datetime
    memory_before: float
    memory_after: float
    cpu_percent: float
    details: Dict[str, Any] = None


@dataclass
class QueryStats:
    """데이터베이스 쿼리 통계"""

    query: str
    execution_count: int
    total_duration: float
    avg_duration: float
    max_duration: float
    min_duration: float
    last_executed: datetime


class PerformanceProfiler:
    """종합 성능 프로파일러"""

    def __init__(self, max_metrics: int = 1000):
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.query_stats: Dict[str, QueryStats] = {}
        self.function_timings: Dict[str, List[float]] = defaultdict(list)
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "hit_rate": 0.0,
        }
        self._lock = threading.RLock()

    @contextmanager
    def measure(self, operation_name: str, details: Dict = None):
        """성능 측정 컨텍스트 매니저"""
        start_time = time.time()
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        cpu_before = process.cpu_percent()

        try:
            yield
        finally:
            end_time = time.time()
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            duration = end_time - start_time

            metric = PerformanceMetric(
                name=operation_name,
                duration=duration,
                timestamp=datetime.now(),
                memory_before=memory_before,
                memory_after=memory_after,
                cpu_percent=cpu_before,
                details=details or {},
            )

            with self._lock:
                self.metrics.append(metric)
                self.function_timings[operation_name].append(duration)

                # 최근 100개만 유지
                if len(self.function_timings[operation_name]) > 100:
                    self.function_timings[operation_name] = self.function_timings[
                        operation_name
                    ][-100:]

    def profile_function(self, func_name: str = None):
        """함수 프로파일링 데코레이터"""

        def decorator(func: Callable) -> Callable:
            name = func_name or f"{func.__module__}.{func.__name__}"

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.measure(name):
                    return func(*args, **kwargs)

            return wrapper

        return decorator

    def record_query(self, query: str, duration: float):
        """데이터베이스 쿼리 기록"""
        with self._lock:
            query_key = self._normalize_query(query)

            if query_key in self.query_stats:
                stats = self.query_stats[query_key]
                stats.execution_count += 1
                stats.total_duration += duration
                stats.avg_duration = stats.total_duration / stats.execution_count
                stats.max_duration = max(stats.max_duration, duration)
                stats.min_duration = min(stats.min_duration, duration)
                stats.last_executed = datetime.now()
            else:
                self.query_stats[query_key] = QueryStats(
                    query=query_key,
                    execution_count=1,
                    total_duration=duration,
                    avg_duration=duration,
                    max_duration=duration,
                    min_duration=duration,
                    last_executed=datetime.now(),
                )

    def _normalize_query(self, query: str) -> str:
        """쿼리 정규화 (파라미터 제거)"""
        # 간단한 정규화 - 실제로는 더 정교한 파싱이 필요
        import re

        normalized = re.sub(r"'[^']*'", "'?'", query)
        normalized = re.sub(r"\b\d+\b", "?", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def update_cache_stats(self, operation: str):
        """캐시 통계 업데이트"""
        with self._lock:
            if operation in self.cache_stats:
                self.cache_stats[operation] += 1

            # 히트율 계산
            total_attempts = self.cache_stats["hits"] + self.cache_stats["misses"]
            if total_attempts > 0:
                self.cache_stats["hit_rate"] = self.cache_stats["hits"] / total_attempts

    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 반환"""
        with self._lock:
            if not self.metrics:
                return {"status": "no_data"}

            # 최근 메트릭 분석
            recent_metrics = list(self.metrics)[-100:]  # 최근 100개

            summary = {
                "timestamp": datetime.now().isoformat(),
                "total_measurements": len(self.metrics),
                "time_range": {
                    "start": min(m.timestamp for m in recent_metrics).isoformat(),
                    "end": max(m.timestamp for m in recent_metrics).isoformat(),
                },
                "performance": {
                    "avg_duration": sum(m.duration for m in recent_metrics)
                    / len(recent_metrics),
                    "max_duration": max(m.duration for m in recent_metrics),
                    "min_duration": min(m.duration for m in recent_metrics),
                    "total_duration": sum(m.duration for m in recent_metrics),
                },
                "memory": {
                    "avg_usage": sum(m.memory_after for m in recent_metrics)
                    / len(recent_metrics),
                    "max_usage": max(m.memory_after for m in recent_metrics),
                    "avg_growth": sum(
                        m.memory_after - m.memory_before for m in recent_metrics
                    )
                    / len(recent_metrics),
                },
                "function_timings": {
                    name: {
                        "count": len(timings),
                        "avg": sum(timings) / len(timings),
                        "max": max(timings),
                        "min": min(timings),
                        "p95": sorted(timings)[int(len(timings) * 0.95)]
                        if timings
                        else 0,
                    }
                    for name, timings in self.function_timings.items()
                },
                "cache_stats": self.cache_stats.copy(),
                "slow_queries": self._get_slow_queries(),
                "recommendations": self._generate_recommendations(),
            }

            return summary

    def _get_slow_queries(self, threshold: float = 0.1) -> List[Dict]:
        """느린 쿼리 식별"""
        slow_queries = []
        for query, stats in self.query_stats.items():
            if stats.avg_duration > threshold:
                slow_queries.append(
                    {
                        "query": query[:200] + "..." if len(query) > 200 else query,
                        "avg_duration": stats.avg_duration,
                        "max_duration": stats.max_duration,
                        "execution_count": stats.execution_count,
                        "total_time": stats.total_duration,
                    }
                )

        return sorted(slow_queries, key=lambda x: x["total_time"], reverse=True)[:10]

    def _generate_recommendations(self) -> List[str]:
        """성능 개선 권장사항 생성"""
        recommendations = []

        # 캐시 히트율 분석
        if self.cache_stats["hit_rate"] < 0.7:
            recommendations.append(
                f"캐시 히트율이 낮습니다 ({self.cache_stats['hit_rate']:.2%}). TTL 조정 또는 캐시 워밍 고려"
            )

        # 함수 성능 분석
        for name, timings in self.function_timings.items():
            if timings:
                avg_time = sum(timings) / len(timings)
                if avg_time > 0.5:  # 500ms 이상
                    recommendations.append(f"함수 {name}의 평균 실행시간이 깁니다 ({avg_time:.3f}s)")

        # 메모리 사용량 분석
        if self.metrics:
            avg_memory_growth = sum(
                m.memory_after - m.memory_before for m in self.metrics
            ) / len(self.metrics)
            if avg_memory_growth > 10:  # 10MB 이상 증가
                recommendations.append(f"평균 메모리 증가량이 큽니다 ({avg_memory_growth:.1f}MB)")

        # 느린 쿼리 분석
        slow_queries = self._get_slow_queries(0.05)  # 50ms 이상
        if slow_queries:
            recommendations.append(f"{len(slow_queries)}개의 느린 쿼리가 발견되었습니다. 인덱스 최적화 필요")

        return recommendations

    def export_data(self, filepath: str):
        """성능 데이터 내보내기"""
        data = {
            "summary": self.get_performance_summary(),
            "detailed_metrics": [asdict(m) for m in list(self.metrics)],
            "query_stats": {k: asdict(v) for k, v in self.query_stats.items()},
        }

        with open(filepath, "w") as f:
            if HAS_ORJSON:
                f.write(
                    orjson.dumps(data, option=orjson.OPT_INDENT_2, default=str).decode()
                )
            else:
                json.dump(data, f, indent=2, default=str)

        logger.info(f"성능 데이터 내보내기 완료: {filepath}")


class DatabaseProfiler:
    """데이터베이스 특화 프로파일러"""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.profiler = PerformanceProfiler()

    @contextmanager
    def profile_query(self, query: str):
        """쿼리 프로파일링"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.profiler.record_query(query, duration)

    def analyze_indexes(self) -> Dict[str, Any]:
        """인덱스 분석"""
        analysis = {
            "existing_indexes": [],
            "missing_indexes": [],
            "unused_indexes": [],
            "recommendations": [],
        }

        try:
            with self.db_manager.engine.connect() as conn:
                # SQLite 인덱스 정보 조회
                result = conn.execute("PRAGMA index_list")
                for row in result:
                    index_info = conn.execute(f"PRAGMA index_info({row[1]})")
                    columns = [col[2] for col in index_info]
                    analysis["existing_indexes"].append(
                        {
                            "name": row[1],
                            "table": row[2] if len(row) > 2 else "unknown",
                            "unique": bool(row[2]) if len(row) > 2 else False,
                            "columns": columns,
                        }
                    )

                # 테이블별 스캔 분석
                tables = ["blacklist_ip", "ip_detection", "daily_stats"]
                for table in tables:
                    scan_info = self._analyze_table_scans(conn, table)
                    if scan_info["needs_index"]:
                        analysis["missing_indexes"].extend(scan_info["suggestions"])

        except Exception as e:
            logger.error(f"인덱스 분석 실패: {e}")
            analysis["error"] = str(e)

        return analysis

    def _analyze_table_scans(self, conn, table: str) -> Dict:
        """테이블 스캔 분석"""
        scan_info = {"needs_index": False, "suggestions": []}

        try:
            # 자주 사용되는 WHERE 절 패턴 분석
            common_patterns = [
                ("ip_address", "ip_address 컬럼 검색 최적화"),
                ("detection_date", "날짜 범위 검색 최적화"),
                ("category", "카테고리별 분류 최적화"),
            ]

            for column, description in common_patterns:
                # 컬럼이 존재하는지 확인
                try:
                    conn.execute(f"SELECT {column} FROM {table} LIMIT 1")

                    # 기존 인덱스 확인
                    existing = conn.execute(f"PRAGMA index_info({table}_{column}_idx)")
                    if not list(existing):
                        scan_info["needs_index"] = True
                        scan_info["suggestions"].append(
                            {
                                "table": table,
                                "column": column,
                                "description": description,
                                "query": f"CREATE INDEX IF NOT EXISTS idx_{table}_{column} ON {table}({column})",
                            }
                        )
                except:
                    continue

        except Exception as e:
            logger.warning(f"테이블 {table} 스캔 분석 실패: {e}")

        return scan_info

    def optimize_queries(self) -> List[str]:
        """쿼리 최적화 제안"""
        optimizations = []

        for query, stats in self.profiler.query_stats.items():
            if stats.avg_duration > 0.1:  # 100ms 이상
                # 기본 최적화 제안
                suggestions = self._analyze_query_for_optimization(query)
                optimizations.extend(suggestions)

        return optimizations

    def _analyze_query_for_optimization(self, query: str) -> List[str]:
        """개별 쿼리 최적화 분석"""
        suggestions = []
        query_lower = query.lower()

        # SELECT * 사용 확인
        if "select *" in query_lower:
            suggestions.append(f"SELECT * 대신 필요한 컬럼만 선택: {query[:50]}...")

        # JOIN 없는 서브쿼리 확인
        if "in (" in query_lower and "select" in query_lower:
            suggestions.append(f"서브쿼리를 JOIN으로 변경 고려: {query[:50]}...")

        # ORDER BY without LIMIT 확인
        if "order by" in query_lower and "limit" not in query_lower:
            suggestions.append(f"ORDER BY에 LIMIT 추가 고려: {query[:50]}...")

        return suggestions


class CacheProfiler:
    """캐시 성능 프로파일러"""

    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.stats = {
            "operations": defaultdict(int),
            "durations": defaultdict(list),
            "key_patterns": defaultdict(int),
            "size_stats": [],
        }

    def profile_operation(self, operation: str):
        """캐시 작업 프로파일링 데코레이터"""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                self.stats["operations"][operation] += 1
                self.stats["durations"][operation].append(duration)

                # 키 패턴 분석
                if args and isinstance(args[0], str):
                    key_prefix = args[0].split(":")[0] if ":" in args[0] else args[0]
                    self.stats["key_patterns"][key_prefix] += 1

                return result

            return wrapper

        return decorator

    def analyze_cache_efficiency(self) -> Dict[str, Any]:
        """캐시 효율성 분석"""
        analysis = {
            "hit_rate": 0.0,
            "operation_stats": {},
            "key_distribution": dict(self.stats["key_patterns"]),
            "recommendations": [],
        }

        # 작업별 통계
        for op, durations in self.stats["durations"].items():
            if durations:
                analysis["operation_stats"][op] = {
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "max_duration": max(durations),
                    "total_duration": sum(durations),
                }

        # 히트율 계산
        hits = self.stats["operations"].get("get_hit", 0)
        misses = self.stats["operations"].get("get_miss", 0)
        if hits + misses > 0:
            analysis["hit_rate"] = hits / (hits + misses)

        # 권장사항
        if analysis["hit_rate"] < 0.7:
            analysis["recommendations"].append("캐시 히트율이 낮음 - TTL 조정 또는 캐시 워밍 필요")

        if analysis["operation_stats"].get("get", {}).get("avg_duration", 0) > 0.01:
            analysis["recommendations"].append("캐시 조회 시간이 김 - Redis 연결 상태 확인 필요")

        return analysis


class AsyncPerformanceProfiler:
    """비동기 성능 프로파일러"""

    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.profiler = PerformanceProfiler()

    async def measure_async(self, operation_name: str, coro, details: Dict = None):
        """비동기 작업 성능 측정"""
        start_time = time.time()
        try:
            result = await coro
            return result
        finally:
            duration = time.time() - start_time
            # 비동기적으로 메트릭 기록
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                self.executor, self._record_metric, operation_name, duration, details
            )

    def _record_metric(
        self, operation_name: str, duration: float, details: Dict = None
    ):
        """메트릭 기록 (스레드 풀에서 실행)"""
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024

        metric = PerformanceMetric(
            name=operation_name,
            duration=duration,
            timestamp=datetime.now(),
            memory_before=memory_usage,
            memory_after=memory_usage,
            cpu_percent=process.cpu_percent(),
            details=details or {},
        )

        with self.profiler._lock:
            self.profiler.metrics.append(metric)
            self.profiler.function_timings[operation_name].append(duration)


class ResponseOptimizer:
    """응답 최적화 유틸리티"""

    @staticmethod
    def fast_json_response(
        data: Any, status_code: int = 200, headers: Dict = None
    ) -> tuple:
        """빠른 JSON 응답 생성"""
        if HAS_ORJSON:
            json_str = orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY).decode()
        else:
            json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

        response_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(json_str.encode("utf-8"))),
            **(headers or {}),
        }

        return json_str, status_code, response_headers

    @staticmethod
    def generate_streaming_response(data_generator, chunk_size: int = 8192):
        """스트리밍 응답 생성기"""

        def generate():
            buffer = []
            buffer_size = 0

            for item in data_generator:
                if HAS_ORJSON:
                    line = orjson.dumps(item).decode() + "\n"
                else:
                    line = json.dumps(item, separators=(",", ":")) + "\n"

                buffer.append(line)
                buffer_size += len(line.encode("utf-8"))

                if buffer_size >= chunk_size:
                    yield "".join(buffer)
                    buffer = []
                    buffer_size = 0

            if buffer:
                yield "".join(buffer)

        return generate()

    @staticmethod
    def optimize_cache_headers(
        max_age: int = 300, etag: str = None, last_modified: datetime = None
    ) -> Dict[str, str]:
        """캐시 헤더 최적화"""
        headers = {
            "Cache-Control": f"public, max-age={max_age}, s-maxage={max_age}",
            "Vary": "Accept-Encoding, Accept",
        }

        if etag:
            headers["ETag"] = f'"{etag}"'

        if last_modified:
            headers["Last-Modified"] = last_modified.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )

        return headers


class ConnectionPoolManager:
    """연결 풀 관리자"""

    def __init__(self, max_connections: int = 20, keepalive_timeout: int = 300):
        self.max_connections = max_connections
        self.keepalive_timeout = keepalive_timeout
        self._pools = {}
        self._lock = threading.RLock()

    def get_pool_config(self) -> Dict[str, Any]:
        """연결 풀 설정 반환"""
        return {
            "pool_size": self.max_connections,
            "max_overflow": self.max_connections // 2,
            "pool_timeout": 30,
            "pool_recycle": self.keepalive_timeout,
            "pool_pre_ping": True,
            "echo": False,
        }

    def get_gunicorn_config(self) -> Dict[str, Any]:
        """Gunicorn 최적화 설정"""
        import multiprocessing

        return {
            "workers": min(multiprocessing.cpu_count() * 2 + 1, 8),
            "worker_class": "sync",
            "worker_connections": 1000,
            "max_requests": 10000,
            "max_requests_jitter": 1000,
            "timeout": 120,
            "keepalive": 5,
            "preload_app": True,
        }


# 글로벌 프로파일러 인스턴스
_global_profiler = None
_async_profiler = None
_response_optimizer = None
_connection_manager = None


def get_profiler() -> PerformanceProfiler:
    """글로벌 프로파일러 인스턴스 반환"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler


def get_async_profiler() -> AsyncPerformanceProfiler:
    """비동기 프로파일러 인스턴스 반환"""
    global _async_profiler
    if _async_profiler is None:
        _async_profiler = AsyncPerformanceProfiler()
    return _async_profiler


def get_response_optimizer() -> ResponseOptimizer:
    """응답 최적화 인스턴스 반환"""
    global _response_optimizer
    if _response_optimizer is None:
        _response_optimizer = ResponseOptimizer()
    return _response_optimizer


def get_connection_manager() -> ConnectionPoolManager:
    """연결 관리자 인스턴스 반환"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionPoolManager()
    return _connection_manager


def profile_function(name: str = None):
    """함수 프로파일링 데코레이터"""
    return get_profiler().profile_function(name)


def measure_performance(operation_name: str, details: Dict = None):
    """성능 측정 컨텍스트 매니저"""
    return get_profiler().measure(operation_name, details)


def benchmark_api_endpoints(
    base_url: str = "http://localhost:2541", iterations: int = 100
) -> Dict[str, Any]:
    """API 엔드포인트 벤치마크"""
    import statistics

    import requests

    endpoints = [
        "/health",
        "/api/blacklist/active",
        "/api/fortigate",
        "/api/stats",
        "/api/search/192.168.1.1",
    ]

    results = {}

    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        times = []
        errors = 0

        for _ in range(iterations):
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                end_time = time.time()

                if response.status_code == 200:
                    times.append(end_time - start_time)
                else:
                    errors += 1
            except Exception:
                errors += 1

        if times:
            results[endpoint] = {
                "avg_time": statistics.mean(times),
                "median_time": statistics.median(times),
                "min_time": min(times),
                "max_time": max(times),
                "p95_time": sorted(times)[int(len(times) * 0.95)]
                if len(times) > 20
                else max(times),
                "success_rate": (iterations - errors) / iterations,
                "total_requests": iterations,
                "errors": errors,
            }
        else:
            results[endpoint] = {
                "error": "All requests failed",
                "errors": errors,
                "total_requests": iterations,
            }

    return results
