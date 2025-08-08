"""
메모리 사용량 최적화 모듈 - Modularized Entry Point

이 모듈은 Blacklist 시스템의 메모리 효율성을 향상시키기 위한
대량 데이터 처리, 메모리 풀링, 가비지 컬렉션 최적화 기능을 제공합니다.

This module now uses modular mixins for better code organization:
- CoreMemoryOptimizer: Core memory monitoring and optimization
- DatabaseOptimizationMixin: Database-specific memory optimizations
- BulkProcessorMixin: Large-scale data processing
- ReportingMixin: Memory usage analysis and reporting
"""


from .memory.bulk_processor import BulkProcessorMixin

# Import modular components
from .memory.core_optimizer import CoreMemoryOptimizer
from .memory.database_operations import DatabaseOptimizationMixin
from .memory.reporting import ReportingMixin


class MemoryOptimizer(
    CoreMemoryOptimizer, DatabaseOptimizationMixin, BulkProcessorMixin, ReportingMixin
):
    """
    메모리 사용량 최적화 관리자 - 모든 기능을 통합

    Uses multiple inheritance with specialized mixins for modular functionality:
    - CoreMemoryOptimizer: Memory monitoring, GC, and basic optimization
    - DatabaseOptimizationMixin: Database operation optimizations
    - BulkProcessorMixin: Large-scale IP processing
    - ReportingMixin: Analysis and recommendations
    """

    def __init__(
        self,
        max_memory_percent: float = 80.0,
        gc_threshold_mb: float = 100.0,
        monitoring_interval: float = 30.0,
    ):
        # Initialize core optimizer (other mixins don't need initialization)
        super().__init__(max_memory_percent, gc_threshold_mb, monitoring_interval)

    # get_memory_stats is now provided by CoreMemoryOptimizer

    # check_memory_pressure is now provided by CoreMemoryOptimizer

    # force_gc_if_needed is now provided by CoreMemoryOptimizer

    # chunked_processing is now provided by CoreMemoryOptimizer

    # get_object_from_pool and return_object_to_pool are now provided by CoreMemoryOptimizer

    # optimize_database_operations is now provided by DatabaseOptimizationMixin

    # efficient_ip_processing is now provided by BulkProcessorMixin

    # start_memory_monitoring, stop_memory_monitoring, and _monitoring_loop are now provided by CoreMemoryOptimizer

    # get_optimization_report and _generate_recommendations are now provided by ReportingMixin


# 글로벌 메모리 최적화기
_global_memory_optimizer = None


def get_global_memory_optimizer() -> MemoryOptimizer:
    """글로벌 메모리 최적화기 반환"""
    global _global_memory_optimizer

    if _global_memory_optimizer is None:
        _global_memory_optimizer = MemoryOptimizer()

    return _global_memory_optimizer


def memory_efficient(chunk_size: int = 1000):
    """메모리 효율적 처리 데코레이터"""

    def decorator(func):
        def wrapper(data, *args, **kwargs):
            optimizer = get_global_memory_optimizer()

            if isinstance(data, list) and len(data) > chunk_size:
                results = []
                with optimizer.chunked_processing(data, chunk_size) as chunks:
                    for chunk_num, chunk, total_chunks in chunks:
                        chunk_result = func(chunk, *args, **kwargs)
                        results.extend(
                            chunk_result
                            if isinstance(chunk_result, list)
                            else [chunk_result]
                        )
                return results
            else:
                return func(data, *args, **kwargs)

        return wrapper

    return decorator


if __name__ == "__main__":
    """메모리 최적화 시스템 검증"""
    import sys

    optimizer = MemoryOptimizer()
    all_tests_passed = True

    try:
        # 테스트 1: 메모리 통계
        stats = optimizer.get_memory_stats()
        if stats.total_memory_mb <= 0:
            print("❌ 메모리 통계 테스트 실패")
            all_tests_passed = False

        # 테스트 2: 청크 처리
        test_data = list(range(10000))
        processed_chunks = 0

        with optimizer.chunked_processing(test_data, chunk_size=1000) as chunks:
            for chunk_num, chunk, total_chunks in chunks:
                processed_chunks += 1
                if len(chunk) > 1000:
                    print("❌ 청크 크기 테스트 실패")
                    all_tests_passed = False

        if processed_chunks != 10:
            print(f"❌ 청크 수 테스트 실패: expected 10, got {processed_chunks}")
            all_tests_passed = False

        # 테스트 3: IP 처리 최적화
        test_ips = [f"192.168.1.{i}" for i in range(1000)] * 2  # 중복 포함
        unique_ips = optimizer.efficient_ip_processing(test_ips)

        if len(unique_ips) != 1000:
            print(f"❌ IP 처리 테스트 실패: expected 1000 unique IPs, got {len(unique_ips)}")
            all_tests_passed = False

        # 테스트 4: 객체 풀
        def list_factory():
            return []

        obj1 = optimizer.get_object_from_pool("test_list", list_factory)
        optimizer.return_object_to_pool("test_list", obj1, lambda x: x.clear())
        obj2 = optimizer.get_object_from_pool("test_list")

        if obj1 is not obj2:
            print("❌ 객체 풀 테스트 실패")
            all_tests_passed = False

        # 최종 보고서
        report = optimizer.get_optimization_report()

        if all_tests_passed:
            print("✅ 메모리 최적화 시스템 검증 완료 - 모든 테스트 통과")
            print(f"📊 메모리 사용량: {report['current_memory']['usage_percent']:.1f}%")
            print(f"🎯 최적화 통계: {report['optimization_stats']}")
            sys.exit(0)
        else:
            print("❌ 일부 테스트 실패")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
