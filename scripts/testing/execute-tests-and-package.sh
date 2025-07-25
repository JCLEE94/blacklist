#!/bin/bash
# 테스트 실행 및 오프라인 패키지 생성

echo "🧪 통합 테스트 실행 중..."
cd /home/jclee/app/blacklist

# Python 경로 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 모든 통합 테스트 실행
echo "📋 전체 통합 테스트 실행..."
python3 tests/integration/run_all_integration_tests.py

# 테스트 결과 확인
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ 모든 테스트 통과!"
    
    # 오프라인 패키지 생성
    echo ""
    echo "📦 오프라인 패키지 생성 시작..."
    chmod +x scripts/create-offline-package-minimal.sh
    ./scripts/create-offline-package-minimal.sh
    
    echo ""
    echo "✅ 작업 완료!"
else
    echo "❌ 테스트 실패! 오프라인 패키지를 생성하지 않습니다."
    exit 1
fi