"""
메모리 최적화 보고 및 분석

메모리 사용 패턴 분석, 최적화 성과 보고, 및 바이온 세그맨테이션을 제공합니다.
"""

from typing import Any
from typing import Dict
from typing import List


class ReportingMixin:
    """메모리 최적화 보고 및 분석 믹스인"""

    def get_optimization_report(self) -> Dict[str, Any]:
        """메모리 최적화 보고서"""
        current_stats = self.get_memory_stats()

        # 풀 효율성 계산
        total_pool_requests = (
            self.optimization_stats["pool_hits"]
            + self.optimization_stats["pool_misses"]
        )
        pool_hit_rate = (
            self.optimization_stats["pool_hits"] / total_pool_requests * 100
            if total_pool_requests > 0
            else 0
        )

        # 메모리 히스토리 분석
        if len(self.memory_history) > 1:
            memory_trend = (
                self.memory_history[-1].memory_percent
                - self.memory_history[0].memory_percent
            )
        else:
            memory_trend = 0

        return {
            "current_memory": {
                "total_mb": current_stats.total_memory_mb,
                "used_mb": current_stats.used_memory_mb,
                "available_mb": current_stats.available_memory_mb,
                "usage_percent": current_stats.memory_percent,
                "process_mb": current_stats.process_memory_mb,
            },
            "optimization_stats": {
                **self.optimization_stats,
                "pool_hit_rate_percent": round(pool_hit_rate, 2),
                "memory_trend_percent": round(memory_trend, 2),
            },
            "pool_status": {
                pool_type: len(objects)
                for pool_type, objects in self.object_pools.items()
            },
            "recommendations": self._generate_recommendations(current_stats),
            "timestamp": current_stats.timestamp.isoformat(),
        }

    def _generate_recommendations(self, stats) -> List[str]:
        """메모리 최적화 권장사항 생성"""
        recommendations = []

        if stats.memory_percent > 90:
            recommendations.append(
                "🚨 Critical: System memory usage > 90%. Immediate optimization needed."
            )
        elif stats.memory_percent > 80:
            recommendations.append(
                "⚠️ Warning: High memory usage. Consider enabling chunked processing."
            )

        if stats.process_memory_mb > 500:
            recommendations.append(
                "💡 Process memory > 500MB. Consider using object pools."
            )

        if self.optimization_stats["gc_forced"] > 10:
            recommendations.append(
                "🔄 Frequent GC detected. Review data processing patterns."
            )

        pool_efficiency = (
            self.optimization_stats["pool_hits"]
            / (
                self.optimization_stats["pool_hits"]
                + self.optimization_stats["pool_misses"]
            )
            if self.optimization_stats["pool_hits"]
            + self.optimization_stats["pool_misses"]
            > 0
            else 0
        )

        if pool_efficiency < 0.5:
            recommendations.append(
                "📊 Low object pool efficiency. Review pool usage patterns."
            )

        if not recommendations:
            recommendations.append("✅ Memory usage is optimal.")

        return recommendations
