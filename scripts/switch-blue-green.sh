#!/bin/bash
# Blue-Green 전환 스크립트 - 충돌 없는 배포

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Blue-Green Deployment Switch${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 현재 활성 버전 확인
CURRENT=$(kubectl get service blacklist-active -n blacklist -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "none")
echo -e "현재 활성 버전: ${GREEN}$CURRENT${NC}"

# 전환 대상 결정
if [ "$CURRENT" == "blue" ]; then
    TARGET="green"
    TARGET_COLOR=$GREEN
else
    TARGET="blue"
    TARGET_COLOR=$BLUE
fi

echo -e "전환 대상: ${TARGET_COLOR}$TARGET${NC}"
echo ""

# Green 환경 상태 확인
echo "1. $TARGET 환경 상태 확인..."
kubectl get pods -n blacklist -l version=$TARGET

# 헬스체크
echo ""
echo "2. $TARGET 환경 헬스체크..."
if [ "$TARGET" == "green" ]; then
    TEST_PORT=32543
else
    TEST_PORT=32542
fi

HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://192.168.50.110:$TEST_PORT/health || echo "000")
if [ "$HEALTH_CHECK" == "200" ]; then
    echo -e "${GREEN}✓ 헬스체크 성공${NC}"
else
    echo -e "${RED}✗ 헬스체크 실패 (HTTP $HEALTH_CHECK)${NC}"
    echo "전환을 중단합니다."
    exit 1
fi

# 전환 확인
echo ""
read -p "정말 $TARGET 으로 전환하시겠습니까? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "전환 취소"
    exit 0
fi

# Service 전환
echo ""
echo "3. Service 전환 중..."
kubectl patch service blacklist-active -n blacklist -p '{"spec":{"selector":{"version":"'$TARGET'"}}}'

# 전환 확인
echo ""
echo "4. 전환 결과 확인..."
sleep 2
NEW_VERSION=$(kubectl get service blacklist-active -n blacklist -o jsonpath='{.spec.selector.version}')
if [ "$NEW_VERSION" == "$TARGET" ]; then
    echo -e "${GREEN}✓ 성공적으로 $TARGET 으로 전환되었습니다!${NC}"
    echo ""
    echo "접속 URL: http://192.168.50.110:32542"
    echo "이전 버전은 포트 32543에서 계속 실행 중입니다."
else
    echo -e "${RED}✗ 전환 실패${NC}"
    exit 1
fi