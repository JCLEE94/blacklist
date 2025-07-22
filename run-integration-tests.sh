#!/bin/bash
# 통합 테스트 실행 스크립트

echo "🧪 통합 테스트 실행 중..."

# Python 경로 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 테스트 실행
python3 tests/integration/run_all_integration_tests.py

# 개별 테스트 실행 (옵션)
if [ "$1" == "individual" ]; then
    echo ""
    echo "📋 개별 테스트 실행:"
    python3 tests/integration/test_unified_routes_integration.py
    python3 tests/integration/test_collection_system_integration.py
    python3 tests/integration/test_deployment_integration.py
    python3 tests/integration/test_cicd_pipeline_integration.py
    python3 tests/integration/test_e2e_integration.py
fi