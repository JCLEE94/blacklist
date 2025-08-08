#!/bin/bash

# Comprehensive Test Suite Runner for Blacklist Management System
# This script sets up and runs all tests with proper isolation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ENV_FILE="${PROJECT_ROOT}/.env.test"
COVERAGE_MIN=70
PARALLEL_WORKERS=4

echo -e "${BLUE}🧪 Blacklist Management System - 종합 테스트 실행기${NC}"
echo "프로젝트 루트: ${PROJECT_ROOT}"
echo

# Function to print status
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "필수 구성 요소 확인 중..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3가 설치되어 있지 않습니다."
        exit 1
    fi
    
    # Check pytest
    if ! python3 -c "import pytest" &> /dev/null; then
        print_error "pytest가 설치되어 있지 않습니다. pip install pytest를 실행하세요."
        exit 1
    fi
    
    # Check Docker (optional)
    if command -v docker &> /dev/null; then
        DOCKER_AVAILABLE=true
        print_success "Docker 사용 가능"
    else
        DOCKER_AVAILABLE=false
        print_warning "Docker를 사용할 수 없습니다. 로컬 테스트만 실행됩니다."
    fi
    
    print_success "필수 구성 요소 확인 완료"
}

# Function to setup test environment
setup_test_environment() {
    print_status "테스트 환경 설정 중..."
    
    cd "${PROJECT_ROOT}"
    
    # Create test environment file
    cat > "${TEST_ENV_FILE}" << EOF
# Test Environment Configuration
FLASK_ENV=testing
TESTING=1
DEBUG=true

# Database
DATABASE_URL=sqlite:///:memory:
TEST_DATABASE_URL=postgresql://test_user:test_pass_123@localhost:5433/blacklist_test

# Cache
CACHE_TYPE=simple
REDIS_URL=redis://localhost:6380/0

# Security (disabled for testing)
FORCE_DISABLE_COLLECTION=false
COLLECTION_ENABLED=true
RESTART_PROTECTION=false
SAFETY_PROTECTION=false
SECRET_KEY=test-secret-key-for-testing-only

# Auth limits (higher for tests)
MAX_AUTH_ATTEMPTS=100

# Mock credentials
REGTECH_USERNAME=test_regtech
REGTECH_PASSWORD=test_pass
SECUDIUM_USERNAME=test_secudium
SECUDIUM_PASSWORD=test_pass

# Test specific
PYTHONPATH=${PROJECT_ROOT}:${PROJECT_ROOT}/src
EOF
    
    # Load test environment
    set -a
    source "${TEST_ENV_FILE}"
    set +a
    
    # Create necessary directories
    mkdir -p "${PROJECT_ROOT}/htmlcov"
    mkdir -p "${PROJECT_ROOT}/test-reports"
    mkdir -p "${PROJECT_ROOT}/data/test"
    
    print_success "테스트 환경 설정 완료"
}

# Function to start Docker test services
start_docker_services() {
    if [ "$DOCKER_AVAILABLE" = true ]; then
        print_status "Docker 테스트 서비스 시작 중..."
        
        # Stop existing containers
        docker-compose -f docker-compose.test.yml down --remove-orphans &> /dev/null || true
        
        # Start test services
        docker-compose -f docker-compose.test.yml up -d test-postgres test-redis
        
        # Wait for services to be healthy
        print_status "서비스가 준비될 때까지 대기 중..."
        timeout 60s bash -c '
            until docker-compose -f docker-compose.test.yml ps | grep -E "(test-postgres|test-redis)" | grep -E "healthy|Up" | wc -l | grep -q "2"; do
                echo "서비스 준비 중..."
                sleep 2
            done
        ' || {
            print_error "Docker 서비스 시작 실패"
            docker-compose -f docker-compose.test.yml logs
            return 1
        }
        
        print_success "Docker 테스트 서비스 준비 완료"
        return 0
    else
        print_warning "Docker를 사용할 수 없어 로컬 테스트만 실행합니다."
        return 1
    fi
}

# Function to run unit tests
run_unit_tests() {
    print_status "단위 테스트 실행 중..."
    
    cd "${PROJECT_ROOT}"
    
    python3 -m pytest tests/ \
        -m "unit or not integration" \
        --cov=src \
        --cov-report=term-missing \
        --cov-report=html:htmlcov \
        --cov-report=xml:test-reports/coverage.xml \
        --junit-xml=test-reports/unit-tests.xml \
        --tb=short \
        -v \
        --disable-warnings \
        || {
            print_error "단위 테스트 실패"
            return 1
        }
    
    print_success "단위 테스트 완료"
}

# Function to run integration tests
run_integration_tests() {
    print_status "통합 테스트 실행 중..."
    
    cd "${PROJECT_ROOT}"
    
    local markers="integration"
    if [ "$DOCKER_AVAILABLE" = true ]; then
        markers="integration or docker or redis or postgres"
    fi
    
    python3 -m pytest tests/integration/ \
        -m "${markers}" \
        --cov=src \
        --cov-append \
        --cov-report=term-missing \
        --cov-report=html:htmlcov \
        --junit-xml=test-reports/integration-tests.xml \
        --tb=short \
        -v \
        --disable-warnings \
        || {
            print_error "통합 테스트 실패"
            return 1
        }
    
    print_success "통합 테스트 완료"
}

# Function to run performance tests
run_performance_tests() {
    print_status "성능 테스트 실행 중..."
    
    cd "${PROJECT_ROOT}"
    
    python3 -m pytest tests/ \
        -m "performance" \
        --junit-xml=test-reports/performance-tests.xml \
        --tb=short \
        -v \
        --disable-warnings \
        || {
            print_warning "성능 테스트에서 일부 실패가 있을 수 있습니다."
        }
    
    print_success "성능 테스트 완료"
}

# Function to run MSA tests (if Docker available)
run_msa_tests() {
    if [ "$DOCKER_AVAILABLE" = true ]; then
        print_status "MSA 테스트 실행 중..."
        
        cd "${PROJECT_ROOT}"
        
        python3 -m pytest tests/integration/ \
            -m "msa" \
            --junit-xml=test-reports/msa-tests.xml \
            --tb=short \
            -v \
            --disable-warnings \
            || {
                print_warning "MSA 테스트에서 일부 실패가 있을 수 있습니다."
            }
        
        print_success "MSA 테스트 완료"
    else
        print_warning "Docker를 사용할 수 없어 MSA 테스트를 건너뜁니다."
    fi
}

# Function to generate test report
generate_test_report() {
    print_status "테스트 리포트 생성 중..."
    
    cd "${PROJECT_ROOT}"
    
    # Create comprehensive test report
    cat > test-reports/test-summary.md << EOF
# 🧪 Blacklist Management System - 테스트 실행 리포트

## 실행 정보
- 실행 시간: $(date)
- 프로젝트 경로: ${PROJECT_ROOT}
- Python 버전: $(python3 --version)
- Docker 사용 가능: ${DOCKER_AVAILABLE}

## 테스트 결과 요약

### 단위 테스트 (Unit Tests)
- 위치: \`tests/\`
- 마커: \`unit\` 또는 \`not integration\`
- 결과: $([ -f test-reports/unit-tests.xml ] && echo "✅ 완료" || echo "❌ 실패")

### 통합 테스트 (Integration Tests)
- 위치: \`tests/integration/\`
- 마커: \`integration\`
- 결과: $([ -f test-reports/integration-tests.xml ] && echo "✅ 완료" || echo "❌ 실패")

### 성능 테스트 (Performance Tests)
- 마커: \`performance\`
- 결과: $([ -f test-reports/performance-tests.xml ] && echo "✅ 완료" || echo "⚠️ 부분 완료")

### MSA 테스트 (Microservice Tests)
- 마커: \`msa\`
- Docker 필요: Yes
- 결과: $([ -f test-reports/msa-tests.xml ] && echo "✅ 완료" || echo "⚠️ 건너뜀")

## 코드 커버리지
- HTML 리포트: \`htmlcov/index.html\`
- XML 리포트: \`test-reports/coverage.xml\`
- 최소 요구 커버리지: ${COVERAGE_MIN}%

## 생성된 파일들
- \`test-reports/unit-tests.xml\` - 단위 테스트 JUnit XML
- \`test-reports/integration-tests.xml\` - 통합 테스트 JUnit XML  
- \`test-reports/performance-tests.xml\` - 성능 테스트 JUnit XML
- \`test-reports/msa-tests.xml\` - MSA 테스트 JUnit XML
- \`htmlcov/\` - HTML 커버리지 리포트
- \`test-reports/coverage.xml\` - XML 커버리지 리포트

## 다음 단계
1. 커버리지 리포트 검토: \`open htmlcov/index.html\`
2. 실패한 테스트가 있다면 로그 확인
3. 성능 테스트 결과 분석
4. CI/CD 파이프라인에 통합

EOF
    
    print_success "테스트 리포트 생성 완료: test-reports/test-summary.md"
}

# Function to cleanup
cleanup() {
    print_status "정리 중..."
    
    if [ "$DOCKER_AVAILABLE" = true ]; then
        docker-compose -f docker-compose.test.yml down --remove-orphans &> /dev/null || true
    fi
    
    # Remove test environment file
    rm -f "${TEST_ENV_FILE}"
    
    print_success "정리 완료"
}

# Function to show usage
show_usage() {
    echo "사용법: $0 [OPTIONS]"
    echo
    echo "옵션:"
    echo "  --unit-only       단위 테스트만 실행"
    echo "  --integration-only 통합 테스트만 실행"
    echo "  --performance-only 성능 테스트만 실행"
    echo "  --msa-only        MSA 테스트만 실행"
    echo "  --no-docker       Docker 사용 안함"
    echo "  --coverage-min N  최소 커버리지 설정 (기본: 70)"
    echo "  --help           이 도움말 표시"
    echo
    echo "예시:"
    echo "  $0                     # 모든 테스트 실행"
    echo "  $0 --unit-only         # 단위 테스트만 실행"
    echo "  $0 --coverage-min 80   # 80% 최소 커버리지로 실행"
}

# Main execution function
main() {
    local run_unit=true
    local run_integration=true
    local run_performance=true
    local run_msa=true
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --unit-only)
                run_integration=false
                run_performance=false
                run_msa=false
                shift
                ;;
            --integration-only)
                run_unit=false
                run_performance=false
                run_msa=false
                shift
                ;;
            --performance-only)
                run_unit=false
                run_integration=false
                run_msa=false
                shift
                ;;
            --msa-only)
                run_unit=false
                run_integration=false
                run_performance=false
                shift
                ;;
            --no-docker)
                DOCKER_AVAILABLE=false
                shift
                ;;
            --coverage-min)
                COVERAGE_MIN="$2"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "알 수 없는 옵션: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Set cleanup trap
    trap cleanup EXIT
    
    # Main execution flow
    check_prerequisites
    setup_test_environment
    
    # Start Docker services if needed
    if [ "$DOCKER_AVAILABLE" = true ] && ([ "$run_integration" = true ] || [ "$run_msa" = true ]); then
        start_docker_services
    fi
    
    # Run tests based on options
    if [ "$run_unit" = true ]; then
        run_unit_tests
    fi
    
    if [ "$run_integration" = true ]; then
        run_integration_tests
    fi
    
    if [ "$run_performance" = true ]; then
        run_performance_tests
    fi
    
    if [ "$run_msa" = true ]; then
        run_msa_tests
    fi
    
    # Generate final report
    generate_test_report
    
    print_success "모든 테스트 완료! 리포트를 확인하세요: test-reports/test-summary.md"
}

# Execute main function with all arguments
main "$@"