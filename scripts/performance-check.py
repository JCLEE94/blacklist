#!/usr/bin/env python3
"""
Performance optimization and monitoring script for Blacklist Management System
"""
import time
import subprocess
import psutil
from pathlib import Path


def check_system_resources():
    """Check system resource usage"""
    print("🔍 시스템 리소스 검사...")

    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"   💻 CPU 사용률: {cpu_percent}%")

    # Memory usage
    memory = psutil.virtual_memory()
    print(f"   🧠 메모리 사용률: {memory.percent}%")
    print(f"   📊 사용 가능 메모리: {memory.available // (1024**2)} MB")

    # Disk usage
    disk = psutil.disk_usage(".")
    disk_percent = (disk.used / disk.total) * 100
    print(f"   💾 디스크 사용률: {disk_percent:.1f}%")

    return {"cpu": cpu_percent, "memory": memory.percent, "disk": disk_percent}


def check_project_size():
    """Check project directory sizes"""
    print("\n📁 프로젝트 크기 분석...")

    # Get directory sizes
    dirs_to_check = [".", "src", "tests", "data", "logs", "docker"]
    sizes = {}

    for dir_name in dirs_to_check:
        if Path(dir_name).exists():
            try:
                result = subprocess.run(
                    ["du", "-sh", dir_name], capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    size = result.stdout.split("\t")[0]
                    sizes[dir_name] = size
                    print(f"   📂 {dir_name}: {size}")
            except subprocess.TimeoutExpired:
                print(f"   ⚠️ {dir_name}: 타임아웃")

    return sizes


def check_python_imports():
    """Check for slow imports"""
    print("\n🐍 Python 임포트 성능 검사...")

    import_tests = [
        "import flask",
        "import src.core.main",
        "import src.core.minimal_app",
        "import pytest",
    ]

    for import_test in import_tests:
        try:
            start_time = time.time()
            exec(import_test)
            import_time = (time.time() - start_time) * 1000
            status = "✅" if import_time < 100 else "⚠️" if import_time < 500 else "❌"
            print(f"   {status} {import_test}: {import_time:.1f}ms")
        except ImportError as e:
            print(f"   ❌ {import_test}: ImportError - {e}")
        except Exception as e:
            print(f"   ⚠️ {import_test}: {e}")


def optimize_recommendations():
    """Generate optimization recommendations"""
    print("\n💡 최적화 권장사항:")

    recommendations = []

    # Check test coverage files
    htmlcov_path = Path("htmlcov")
    if htmlcov_path.exists():
        recommendations.append("🧹 htmlcov 디렉토리 정리 (테스트 커버리지 파일)")

    # Check cache directories
    cache_dirs = [".pytest_cache", "__pycache__", ".coverage"]
    for cache_dir in cache_dirs:
        if Path(cache_dir).exists():
            recommendations.append(f"🗑️ {cache_dir} 캐시 정리")

    # Check large files
    try:
        result = subprocess.run(
            ["find", ".", "-type", "f", "-size", "+10M"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.stdout.strip():
            recommendations.append("📦 대용량 파일 확인 및 정리")
    except:
        pass

    if recommendations:
        for rec in recommendations:
            print(f"   {rec}")
    else:
        print("   ✅ 추가 최적화 불필요")


def main():
    """Main performance check function"""
    print("🚀 Blacklist 시스템 성능 검사 시작")
    print("=" * 50)

    # Resource check
    resources = check_system_resources()

    # Project size check
    sizes = check_project_size()

    # Import performance
    check_python_imports()

    # Optimization recommendations
    optimize_recommendations()

    # Summary
    print("\n" + "=" * 50)
    print("📊 성능 검사 완료")

    # Performance score calculation
    score = 100
    if resources["cpu"] > 80:
        score -= 20
    if resources["memory"] > 80:
        score -= 20
    if resources["disk"] > 80:
        score -= 10

    performance_level = (
        "우수" if score >= 80 else "양호" if score >= 60 else "개선 필요"
    )
    print(f"🎯 전체 성능 점수: {score}/100 ({performance_level})")

    return score


if __name__ == "__main__":
    main()
