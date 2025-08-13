#!/bin/bash
# REGTECH 일일 수집 cron 설정 스크립트

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔧 REGTECH 일일 수집 CRON 설정"
echo "================================"

# 환경 변수 파일 생성
ENV_FILE="$PROJECT_DIR/.env.cron"

if [ ! -f "$ENV_FILE" ]; then
    echo "📝 환경 변수 파일 생성 중..."
    cat > "$ENV_FILE" << EOF
# REGTECH 자격 증명
export REGTECH_USERNAME="${REGTECH_USERNAME:-}"
export REGTECH_PASSWORD="${REGTECH_PASSWORD:-}"

# Python 경로
export PYTHONPATH="$PROJECT_DIR"

# 로그 디렉토리
export LOG_DIR="$PROJECT_DIR/logs"
EOF
    echo "✅ 환경 변수 파일 생성됨: $ENV_FILE"
    echo "⚠️  REGTECH_USERNAME과 REGTECH_PASSWORD를 설정하세요!"
fi

# 실행 스크립트 생성
RUNNER_SCRIPT="$SCRIPT_DIR/run_regtech_daily.sh"
cat > "$RUNNER_SCRIPT" << EOF
#!/bin/bash
# REGTECH 일일 수집 실행 스크립트

# 프로젝트 디렉토리로 이동
cd "$PROJECT_DIR"

# 환경 변수 로드
source "$ENV_FILE"

# 로그 디렉토리 생성
mkdir -p \$LOG_DIR

# 날짜 정보
DATE=\$(date '+%Y-%m-%d %H:%M:%S')
echo "[\$DATE] REGTECH 일일 수집 시작" >> \$LOG_DIR/regtech_cron.log

# Python 스크립트 실행
/usr/bin/python3 "$SCRIPT_DIR/regtech_daily_collector.py" >> \$LOG_DIR/regtech_cron.log 2>&1

# 종료 상태 확인
if [ \$? -eq 0 ]; then
    echo "[\$DATE] REGTECH 일일 수집 완료" >> \$LOG_DIR/regtech_cron.log
else
    echo "[\$DATE] REGTECH 일일 수집 실패" >> \$LOG_DIR/regtech_cron.log
fi

echo "" >> \$LOG_DIR/regtech_cron.log
EOF

chmod +x "$RUNNER_SCRIPT"
echo "✅ 실행 스크립트 생성됨: $RUNNER_SCRIPT"

# Cron 항목 생성
echo ""
echo "📋 Crontab에 추가할 내용:"
echo "========================================"
echo "# REGTECH 일일 수집 (매일 오전 6시)"
echo "0 6 * * * $RUNNER_SCRIPT"
echo ""
echo "# REGTECH 일일 수집 (6시간마다 - 더 자주 실행)"
echo "0 */6 * * * $RUNNER_SCRIPT"
echo ""
echo "# REGTECH 일일 수집 (매일 오전 9시, 오후 3시, 오후 9시)"
echo "0 9,15,21 * * * $RUNNER_SCRIPT"
echo "========================================"

echo ""
echo "🔧 Crontab 편집 방법:"
echo "  1. crontab -e"
echo "  2. 위의 내용 중 하나를 선택하여 추가"
echo "  3. 저장 후 종료"
echo ""
echo "📊 로그 확인:"
echo "  tail -f $PROJECT_DIR/logs/regtech_cron.log"
echo ""

# 현재 crontab 확인
echo "📌 현재 설정된 crontab:"
crontab -l 2>/dev/null | grep -i regtech || echo "  (REGTECH 관련 설정 없음)"

echo ""
echo "💡 팁: 매일 수집 외에도 6개월 전체 수집을 주기적으로 실행하려면:"
echo "  # 매주 일요일 새벽 2시에 6개월 전체 수집"
echo "  0 2 * * 0 cd $PROJECT_DIR && /usr/bin/python3 scripts/regtech_collect_6months.py >> logs/regtech_weekly.log 2>&1"