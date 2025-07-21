#!/bin/bash
# CI/CD 파이프라인 모니터링 및 알림 시스템

set -e

# 설정
METRICS_FILE="/tmp/blacklist-cicd-metrics.json"
ALERT_LOG="/tmp/blacklist-cicd-alerts.log"
WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
ALERT_EMAIL="${ALERT_EMAIL:-}"

# 메트릭 임계값
THRESHOLD_BUILD_TIME=600        # 10분
THRESHOLD_DEPLOY_TIME=300       # 5분
THRESHOLD_FAILURE_RATE=0.2      # 20%
THRESHOLD_ROLLBACK_COUNT=2      # 2회

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 로깅 함수
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $@" | tee -a "$ALERT_LOG"
}

# 알림 발송
send_alert() {
    local level=$1
    local title=$2
    local message=$3
    local details=$4
    
    log "[$level] $title: $message"
    
    # Slack 알림
    if [ -n "$WEBHOOK_URL" ]; then
        local color="good"
        case "$level" in
            ERROR) color="danger" ;;
            WARNING) color="warning" ;;
        esac
        
        curl -X POST "$WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d @- <<EOF
{
    "attachments": [{
        "color": "$color",
        "title": "$title",
        "text": "$message",
        "fields": [{
            "title": "Details",
            "value": "$details",
            "short": false
        }],
        "footer": "Blacklist CI/CD Monitor",
        "ts": $(date +%s)
    }]
}
EOF
    fi
    
    # 이메일 알림
    if [ -n "$ALERT_EMAIL" ]; then
        echo -e "Subject: [Blacklist CI/CD] $title\n\n$message\n\nDetails:\n$details" | \
            sendmail "$ALERT_EMAIL" 2>/dev/null || true
    fi
}

# 메트릭 수집
collect_metrics() {
    local pipeline_id=$1
    local stage=$2
    local status=$3
    local duration=$4
    
    # 기존 메트릭 로드
    local metrics="{}"
    if [ -f "$METRICS_FILE" ]; then
        metrics=$(cat "$METRICS_FILE")
    fi
    
    # 새 메트릭 추가
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    metrics=$(echo "$metrics" | jq \
        --arg id "$pipeline_id" \
        --arg stage "$stage" \
        --arg status "$status" \
        --arg duration "$duration" \
        --arg timestamp "$timestamp" \
        '.pipelines[$id].stages[$stage] = {
            status: $status,
            duration: ($duration | tonumber),
            timestamp: $timestamp
        }')
    
    echo "$metrics" > "$METRICS_FILE"
}

# 파이프라인 분석
analyze_pipeline() {
    if [ ! -f "$METRICS_FILE" ]; then
        return
    fi
    
    local metrics=$(cat "$METRICS_FILE")
    
    # 최근 24시간 데이터 분석
    local cutoff_time=$(date -u -d '24 hours ago' +"%Y-%m-%dT%H:%M:%SZ")
    
    # 실패율 계산
    local total_builds=$(echo "$metrics" | jq '[.pipelines[].stages.build] | length')
    local failed_builds=$(echo "$metrics" | jq '[.pipelines[].stages.build | select(.status == "failed")] | length')
    
    if [ "$total_builds" -gt 0 ]; then
        local failure_rate=$(echo "scale=2; $failed_builds / $total_builds" | bc)
        
        if (( $(echo "$failure_rate > $THRESHOLD_FAILURE_RATE" | bc -l) )); then
            send_alert "WARNING" "높은 빌드 실패율" \
                "최근 24시간 빌드 실패율: ${failure_rate}% (임계값: ${THRESHOLD_FAILURE_RATE}%)" \
                "총 빌드: $total_builds, 실패: $failed_builds"
        fi
    fi
    
    # 평균 빌드 시간
    local avg_build_time=$(echo "$metrics" | jq '
        [.pipelines[].stages.build | select(.status == "success") | .duration] |
        if length > 0 then add / length else 0 end
    ')
    
    if (( $(echo "$avg_build_time > $THRESHOLD_BUILD_TIME" | bc -l) )); then
        send_alert "WARNING" "빌드 시간 초과" \
            "평균 빌드 시간: ${avg_build_time}초 (임계값: ${THRESHOLD_BUILD_TIME}초)" \
            "빌드 최적화가 필요할 수 있습니다"
    fi
}

# 배포 상태 모니터링
monitor_deployment() {
    local namespace=$1
    local deployment=$2
    
    # Pod 상태 확인
    local ready_pods=$(kubectl get deployment "$deployment" -n "$namespace" \
        -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
    local desired_pods=$(kubectl get deployment "$deployment" -n "$namespace" \
        -o jsonpath='{.spec.replicas}' 2>/dev/null || echo 0)
    
    if [ "$ready_pods" -lt "$desired_pods" ]; then
        local pod_status=$(kubectl get pods -n "$namespace" \
            -l app="$deployment" --no-headers | grep -v Running || true)
        
        send_alert "ERROR" "배포 상태 이상" \
            "$namespace/$deployment: $ready_pods/$desired_pods Pods 준비됨" \
            "비정상 Pods:\n$pod_status"
    fi
    
    # 최근 이벤트 확인
    local error_events=$(kubectl get events -n "$namespace" \
        --field-selector type=Warning \
        --sort-by='.lastTimestamp' \
        -o json | jq -r '.items[-5:] | .[] | 
        "\(.lastTimestamp) \(.reason): \(.message)"' 2>/dev/null || true)
    
    if [ -n "$error_events" ]; then
        log "최근 경고 이벤트:\n$error_events"
    fi
}

# 리소스 사용량 모니터링
monitor_resources() {
    # 노드 리소스 확인
    local node_metrics=$(kubectl top nodes --no-headers 2>/dev/null || true)
    
    if [ -n "$node_metrics" ]; then
        while read -r node cpu_percent cpu_cores memory_percent memory_size; do
            cpu_value=${cpu_percent%\%}
            memory_value=${memory_percent%\%}
            
            if [ "$cpu_value" -gt 80 ]; then
                send_alert "WARNING" "높은 CPU 사용률" \
                    "노드 $node: CPU $cpu_percent" \
                    "즉시 확인이 필요합니다"
            fi
            
            if [ "$memory_value" -gt 85 ]; then
                send_alert "WARNING" "높은 메모리 사용률" \
                    "노드 $node: Memory $memory_percent" \
                    "메모리 부족 위험"
            fi
        done <<< "$node_metrics"
    fi
}

# 롤백 감지
detect_rollbacks() {
    local namespace=$1
    local deployment=$2
    
    # 최근 롤백 이벤트 확인
    local rollback_count=$(kubectl rollout history deployment/"$deployment" \
        -n "$namespace" 2>/dev/null | grep -c "Rollback" || echo 0)
    
    if [ "$rollback_count" -ge "$THRESHOLD_ROLLBACK_COUNT" ]; then
        send_alert "ERROR" "빈번한 롤백 감지" \
            "$namespace/$deployment: 최근 롤백 $rollback_count회" \
            "배포 안정성 점검이 필요합니다"
    fi
}

# GitHub Actions 상태 확인
check_github_actions() {
    local repo="JCLEE94/blacklist"
    local token="${GITHUB_TOKEN:-}"
    
    if [ -z "$token" ]; then
        return
    fi
    
    # 최근 워크플로우 실행 확인
    local recent_runs=$(curl -s \
        -H "Authorization: token $token" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$repo/actions/runs?per_page=10" | \
        jq -r '.workflow_runs[] | select(.status == "completed") | 
        {name: .name, conclusion: .conclusion, created_at: .created_at}')
    
    # 실패한 워크플로우 확인
    local failed_count=$(echo "$recent_runs" | jq -s '[.[] | select(.conclusion != "success")] | length')
    
    if [ "$failed_count" -gt 3 ]; then
        send_alert "WARNING" "GitHub Actions 실패 증가" \
            "최근 10개 실행 중 $failed_count개 실패" \
            "CI/CD 파이프라인 점검 필요"
    fi
}

# 메인 모니터링 루프
monitoring_loop() {
    log "CI/CD 모니터링 시작"
    
    while true; do
        # 파이프라인 메트릭 분석
        analyze_pipeline
        
        # 배포 상태 모니터링
        monitor_deployment "blacklist" "blacklist"
        monitor_deployment "blacklist-dev" "blacklist-dev"
        monitor_deployment "blacklist-staging" "blacklist-staging"
        
        # 리소스 모니터링
        monitor_resources
        
        # 롤백 감지
        detect_rollbacks "blacklist" "blacklist"
        
        # GitHub Actions 상태
        check_github_actions
        
        # 60초 대기
        sleep 60
    done
}

# 리포트 생성
generate_report() {
    local period=${1:-"24h"}
    
    echo "=== CI/CD 파이프라인 리포트 ==="
    echo "기간: 최근 $period"
    echo ""
    
    if [ -f "$METRICS_FILE" ]; then
        local metrics=$(cat "$METRICS_FILE")
        
        # 빌드 통계
        echo "## 빌드 통계"
        local total_builds=$(echo "$metrics" | jq '[.pipelines[].stages.build] | length')
        local success_builds=$(echo "$metrics" | jq '[.pipelines[].stages.build | select(.status == "success")] | length')
        local failed_builds=$(echo "$metrics" | jq '[.pipelines[].stages.build | select(.status == "failed")] | length')
        
        echo "- 총 빌드: $total_builds"
        echo "- 성공: $success_builds"
        echo "- 실패: $failed_builds"
        echo "- 성공률: $(echo "scale=2; $success_builds * 100 / $total_builds" | bc)%"
        echo ""
        
        # 평균 시간
        echo "## 평균 소요 시간"
        local avg_build=$(echo "$metrics" | jq '[.pipelines[].stages.build.duration] | add / length')
        local avg_test=$(echo "$metrics" | jq '[.pipelines[].stages.test.duration] | add / length')
        local avg_deploy=$(echo "$metrics" | jq '[.pipelines[].stages.deploy.duration] | add / length')
        
        echo "- 빌드: ${avg_build}초"
        echo "- 테스트: ${avg_test}초"
        echo "- 배포: ${avg_deploy}초"
    fi
    
    # 현재 상태
    echo ""
    echo "## 현재 배포 상태"
    kubectl get deployments -A -l app=blacklist --no-headers | \
        awk '{printf "- %s/%s: %s/%s ready\n", $1, $2, $3, $4}'
}

# 메인 함수
main() {
    local command=${1:-monitor}
    
    case "$command" in
        monitor)
            monitoring_loop
            ;;
        
        report)
            generate_report "${2:-24h}"
            ;;
        
        collect)
            # 메트릭 수집 (CI/CD에서 호출용)
            if [ $# -lt 4 ]; then
                echo "Usage: $0 collect <pipeline_id> <stage> <status> <duration>"
                exit 1
            fi
            collect_metrics "$2" "$3" "$4" "$5"
            ;;
        
        test-alert)
            # 알림 테스트
            send_alert "INFO" "테스트 알림" \
                "CI/CD 모니터링 시스템 테스트" \
                "알림이 정상적으로 작동합니다"
            ;;
        
        *)
            echo "Usage: $0 {monitor|report|collect|test-alert}"
            exit 1
            ;;
    esac
}

# 실행
main "$@"