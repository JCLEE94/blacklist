#!/bin/bash
# 테스트 실패 처리 수정 스크립트

echo "🔧 테스트 실패 처리 수정 중..."

# Color definitions
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. gitops-cicd.yml에서 || true 제거
echo -e "${YELLOW}gitops-cicd.yml 수정 중...${NC}"
if [ -f ".github/workflows/gitops-cicd.yml" ]; then
    # 이미 수정됨 - 확인만
    if grep -q "|| true" .github/workflows/gitops-cicd.yml; then
        echo -e "${RED}❌ 아직 || true가 남아있습니다${NC}"
    else
        echo -e "${GREEN}✅ gitops-cicd.yml 이미 수정됨${NC}"
    fi
fi

# 2. simple-cicd.yml 확인
echo -e "${YELLOW}simple-cicd.yml 확인 중...${NC}"
if [ -f ".github/workflows/simple-cicd.yml" ]; then
    if grep -q "pytest" .github/workflows/simple-cicd.yml; then
        echo -e "${RED}❌ simple-cicd.yml에 테스트가 있습니다${NC}"
    else
        echo -e "${GREEN}✅ simple-cicd.yml에는 테스트가 없습니다${NC}"
    fi
fi

# 3. 테스트 설정 파일 생성
echo -e "${YELLOW}pytest 설정 파일 생성 중...${NC}"
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    -p no:warnings
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
EOF

echo -e "${GREEN}✅ pytest.ini 생성 완료${NC}"

# 4. 테스트 실행 스크립트 생성
echo -e "${YELLOW}테스트 실행 스크립트 생성 중...${NC}"
cat > run-tests.sh << 'EOF'
#!/bin/bash
# 로컬 테스트 실행 스크립트

echo "🧪 테스트 실행 중..."

# Python 환경 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 단위 테스트만 실행
echo "Running unit tests..."
python3 -m pytest tests/ -m "not integration and not slow" -v

# 통합 테스트 실행 (선택적)
if [ "$1" == "all" ]; then
    echo "Running integration tests..."
    python3 -m pytest tests/ -m "integration" -v
fi

# 전체 테스트 실행
if [ "$1" == "full" ]; then
    echo "Running all tests..."
    python3 -m pytest tests/ -v
fi
EOF

chmod +x run-tests.sh
echo -e "${GREEN}✅ run-tests.sh 생성 완료${NC}"

# 5. GitHub Actions 로컬 테스트 스크립트
echo -e "${YELLOW}CI/CD 로컬 테스트 스크립트 생성 중...${NC}"
cat > test-cicd-locally.sh << 'EOF'
#!/bin/bash
# CI/CD 파이프라인 로컬 테스트

echo "🔍 CI/CD 파이프라인 로컬 테스트..."

# 1. 코드 품질 검사
echo "=== Code Quality Check ==="
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
if [ $? -ne 0 ]; then
    echo "❌ Flake8 failed"
    exit 1
fi

black --check src/
if [ $? -ne 0 ]; then
    echo "❌ Black check failed"
    echo "💡 Run 'black src/' to fix"
    exit 1
fi

isort src/ --check-only
if [ $? -ne 0 ]; then
    echo "❌ isort check failed"
    echo "💡 Run 'isort src/' to fix"
    exit 1
fi

# 2. 테스트 실행
echo "=== Running Tests ==="
python3 -m pytest tests/ -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ Tests failed"
    exit 1
fi

echo "✅ All checks passed!"
EOF

chmod +x test-cicd-locally.sh
echo -e "${GREEN}✅ test-cicd-locally.sh 생성 완료${NC}"

# 6. 요약
echo ""
echo -e "${GREEN}=== 수정 완료 ===${NC}"
echo "1. gitops-cicd.yml: 테스트 실패 시 빌드 중단되도록 수정"
echo "2. pytest.ini: 테스트 설정 파일 생성"
echo "3. run-tests.sh: 로컬 테스트 실행 스크립트"
echo "4. test-cicd-locally.sh: CI/CD 파이프라인 로컬 테스트"
echo ""
echo "사용법:"
echo "  ./run-tests.sh         # 단위 테스트만"
echo "  ./run-tests.sh all     # 통합 테스트 포함"
echo "  ./run-tests.sh full    # 전체 테스트"
echo "  ./test-cicd-locally.sh # CI/CD 파이프라인 테스트"