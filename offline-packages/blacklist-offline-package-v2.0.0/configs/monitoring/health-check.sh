#!/bin/bash

# GitOps 안정화 - 종합 헬스체크 스크립트
# 실행: ./monitoring/health-check.sh

set -e

echo "🔍 GitOps 안정화 - 종합 헬스체크 시작"
echo "시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 상태 확인 함수
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        return 0
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# 경고 함수
warn_status() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# 전체 상태 점수
TOTAL_CHECKS=0
PASSED_CHECKS=0

echo "1. 🐳 Docker 서비스 상태"
echo "------------------------"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(blacklist|redis)"
DOCKER_RUNNING=$(docker ps | grep -c blacklist || echo 0)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ $DOCKER_RUNNING -gt 0 ]; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    check_status 0 "Docker 컨테이너 정상 동작 ($DOCKER_RUNNING개)"
else
    check_status 1 "Docker 컨테이너 중단"
fi

echo
echo "2. ☸️ Kubernetes 서비스 상태"
echo "----------------------------"
kubectl get pods -n blacklist --no-headers 2>/dev/null | while read line; do
    POD_NAME=$(echo $line | awk '{print $1}')
    POD_STATUS=$(echo $line | awk '{print $3}')
    if [ "$POD_STATUS" = "Running" ]; then
        echo -e "${GREEN}✅ $POD_NAME: $POD_STATUS${NC}"
    else
        echo -e "${RED}❌ $POD_NAME: $POD_STATUS${NC}"
    fi
done

K8S_RUNNING=$(kubectl get pods -n blacklist --no-headers 2>/dev/null | grep -c "Running" || echo 0)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ $K8S_RUNNING -gt 0 ]; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    check_status 0 "Kubernetes 파드 정상 동작 ($K8S_RUNNING개)"
else
    check_status 1 "Kubernetes 파드 중단"
fi

echo
echo "3. 🌐 서비스 연결성 테스트"
echo "------------------------"
# Docker 서비스 테스트 (포트 32542)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if curl -s -f http://localhost:32542/health >/dev/null 2>&1; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    check_status 0 "Docker 서비스 응답 (포트 32542)"
else
    check_status 1 "Docker 서비스 응답 실패 (포트 32542)"
fi

# K8s NodePort 서비스 테스트 (포트 32543)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if curl -s -f http://localhost:32543/health >/dev/null 2>&1; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    check_status 0 "Kubernetes 서비스 응답 (포트 32543)"
else
    check_status 1 "Kubernetes 서비스 응답 실패 (포트 32543)"
fi

echo
echo "4. 💾 데이터베이스 상태"
echo "---------------------"
DB_SIZE=$(du -h instance/blacklist.db 2>/dev/null | cut -f1 || echo "N/A")
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -f "instance/blacklist.db" ]; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    check_status 0 "데이터베이스 파일 존재 (크기: $DB_SIZE)"
    
    # DB 크기 경고
    DB_SIZE_MB=$(du -m instance/blacklist.db | cut -f1)
    if [ $DB_SIZE_MB -gt 100 ]; then
        warn_status "데이터베이스 크기가 큽니다 (${DB_SIZE}). 정리 권장."
    fi
else
    check_status 1 "데이터베이스 파일 없음"
fi

echo
echo "5. 📝 로그 상태"
echo "---------------"
LOG_SIZE=$(du -sh logs/ 2>/dev/null | cut -f1 || echo "N/A")
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -d "logs" ]; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    check_status 0 "로그 디렉터리 존재 (크기: $LOG_SIZE)"
    
    # 로그 크기 경고
    LOG_SIZE_MB=$(du -m logs/ | cut -f1)
    if [ $LOG_SIZE_MB -gt 5 ]; then
        warn_status "로그 크기가 큽니다 (${LOG_SIZE}). 로테이션 권장."
    fi
else
    check_status 1 "로그 디렉터리 없음"
fi

echo
echo "6. 🔧 시스템 리소스"
echo "------------------"
# 메모리 사용률
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", ($3/$2) * 100.0}')
echo "메모리 사용률: ${MEMORY_USAGE}%"
if [ $(echo "$MEMORY_USAGE > 80.0" | bc -l) -eq 1 ]; then
    warn_status "메모리 사용률이 높습니다 (${MEMORY_USAGE}%)"
fi

# 디스크 사용률
DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
echo "디스크 사용률: ${DISK_USAGE}%"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ $DISK_USAGE -lt 90 ]; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    check_status 0 "디스크 사용률 정상 (${DISK_USAGE}%)"
else
    check_status 1 "디스크 사용률 위험 (${DISK_USAGE}%)"
fi

echo
echo "7. 🚀 CI/CD 파이프라인 상태"
echo "-------------------------"
ACTIVE_WORKFLOWS=$(ls .github/workflows/*.yml 2>/dev/null | wc -l || echo 0)
echo "활성 워크플로우: $ACTIVE_WORKFLOWS개"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ $ACTIVE_WORKFLOWS -le 3 ]; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    check_status 0 "워크플로우 개수 최적화됨 ($ACTIVE_WORKFLOWS개)"
else
    check_status 1 "워크플로우 개수 과다 ($ACTIVE_WORKFLOWS개)"
fi

echo
echo "========================================"
echo "📊 종합 헬스체크 결과"
echo "========================================"

# 점수 계산
HEALTH_SCORE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo "총 검사 항목: $TOTAL_CHECKS"
echo "통과 항목: $PASSED_CHECKS"
echo "실패 항목: $((TOTAL_CHECKS - PASSED_CHECKS))"

if [ $HEALTH_SCORE -ge 90 ]; then
    echo -e "${GREEN}🎉 전체 상태: 우수 (${HEALTH_SCORE}%)${NC}"
elif [ $HEALTH_SCORE -ge 80 ]; then
    echo -e "${YELLOW}⚠️ 전체 상태: 양호 (${HEALTH_SCORE}%)${NC}"
elif [ $HEALTH_SCORE -ge 70 ]; then
    echo -e "${YELLOW}⚠️ 전체 상태: 보통 (${HEALTH_SCORE}%)${NC}"
else
    echo -e "${RED}🚨 전체 상태: 위험 (${HEALTH_SCORE}%)${NC}"
fi

echo
echo "다음 헬스체크: $(date -d '+1 hour' '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 결과를 로그 파일에도 저장
mkdir -p monitoring/logs
echo "$(date '+%Y-%m-%d %H:%M:%S') - Health Score: ${HEALTH_SCORE}%" >> monitoring/logs/health-history.log

exit 0