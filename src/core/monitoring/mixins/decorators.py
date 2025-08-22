"""
Prometheus 메트릭 수집 데코레이터

HTTP 요청 및 데이터 수집 작업 추적을 위한 데코레이터들을 제공합니다.
"""

from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging

logger = logging.getLogger(__name__)

import time


def track_http_requests(func):
    """HTTP 요청 추적 데코레이터"""

    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            # Flask request context에서 정보 추출

            method = request.method
            endpoint = request.endpoint or "unknown"

            result = func(*args, **kwargs)

            # 성공적인 응답
            status_code = getattr(result, "status_code", 200)
            duration = time.time() - start_time

            from ..prometheus_metrics import get_metrics

            metrics = get_metrics()
            metrics.record_http_request(method, endpoint, status_code, duration)

            return result

        except Exception as e:
            # 오류 발생
            duration = time.time() - start_time

            try:

                method = request.method
                endpoint = request.endpoint or "unknown"

                from ..prometheus_metrics import get_metrics

                metrics = get_metrics()
                metrics.record_http_request(method, endpoint, 500, duration)
                metrics.record_error("http_request_error", "web")
            except Exception:
                pass

            raise e

    return wrapper


def track_collection_operation(source: str):
    """데이터 수집 작업 추적 데코레이터"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # 결과에서 수집 정보 추출
                items_count = (
                    {
                        "new": result.get("new_items", 0),
                        "updated": result.get("updated_items", 0),
                        "duplicate": result.get("duplicate_items", 0),
                    }
                    if isinstance(result, dict)
                    else {"total": 1}
                )

                from ..prometheus_metrics import get_metrics

                metrics = get_metrics()
                metrics.record_collection_event(source, True, duration, items_count)

                return result

            except Exception as e:
                duration = time.time() - start_time

                from ..prometheus_metrics import get_metrics

                metrics = get_metrics()
                metrics.record_collection_event(source, False, duration, {})
                metrics.record_error("collection_error", source)

                raise e

        return wrapper

    return decorator
