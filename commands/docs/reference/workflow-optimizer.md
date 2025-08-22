#!/bin/bash
: '
# 🤖 Workflow Optimizer Agent
# 워크플로우 최적화 및 성능 개선 전문 Agent
'

set -euo pipefail

echo "🤖 Workflow Optimizer Agent 실행 중..."
echo "작업: $1"

PARALLEL_EXECUTOR="$HOME/.claude/commands/utils/parallel-executor.md"
CHECKPOINT_MANAGER="$HOME/.claude/commands/utils/workflow-checkpoint.md"

# 워크플로우 최적화 분석
optimize_workflow() {
    local task="$1"
    
    echo "⚡ 워크플로우 최적화 분석 중..."
    
    # 현재 실행 중인 워크플로우 체크포인트 확인
    if [ -x "$CHECKPOINT_MANAGER" ]; then
        echo "📍 체크포인트 상태 확인..."
        "$CHECKPOINT_MANAGER" status
        
        # 실패한 단계가 있는지 확인
        local failed_stage=$("$CHECKPOINT_MANAGER" failed 2>/dev/null || echo "")
        if [ -n "$failed_stage" ]; then
            echo "🔄 실패한 단계 발견: $failed_stage"
            echo "   재시작을 권장합니다."
            
            if [ "$AUTO_APPROVE" != "true" ]; then
                echo "실패한 지점부터 재시작하시겠습니까? (y/n)"
                read -r restart_choice
                if [ "$restart_choice" = "y" ] || [ "$restart_choice" = "Y" ]; then
                    "$CHECKPOINT_MANAGER" resume
                fi
            fi
        fi
    fi
    
    # 병렬 처리 최적화 제안
    suggest_parallel_optimization "$task"
    
    # 워크플로우 성능 분석
    analyze_workflow_performance
    
    # 리소스 사용량 최적화
    optimize_resource_usage
}

# 병렬 처리 최적화 제안
suggest_parallel_optimization() {
    local task="$1"
    
    echo ""
    echo "🔀 병렬 처리 최적화 분석..."
    
    # 현재 병렬 처리 상태 확인
    if [ "${ENABLE_PARALLEL:-true}" = "true" ]; then
        echo "✅ 병렬 처리가 활성화되어 있습니다."
        
        if [ -x "$PARALLEL_EXECUTOR" ]; then
            echo "📊 병렬 실행 상태 확인..."
            "$PARALLEL_EXECUTOR" status
        fi
        
        # 작업별 병렬화 가능성 분석
        case "$task" in
            *"분석"*|*"analysis"*)
                echo "💡 분석 작업은 다음과 같이 병렬화 가능:"
                echo "   • 코드 품질 분석"
                echo "   • 보안 취약점 스캔"
                echo "   • 의존성 검증"
                echo "   • 라이센스 검증"
                ;;
            *"정리"*|*"clean"*)
                echo "💡 정리 작업은 다음과 같이 병렬화 가능:"
                echo "   • 중복 파일 제거"
                echo "   • 코드 포맷팅"
                echo "   • import 정리"
                echo "   • 빌드 아티팩트 정리"
                ;;
            *"테스트"*|*"test"*)
                echo "💡 테스트 작업은 다음과 같이 병렬화 가능:"
                echo "   • 단위 테스트"
                echo "   • 통합 테스트"
                echo "   • 린팅 검사"
                echo "   • 테스트 커버리지 생성"
                ;;
            *"빌드"*|*"build"*)
                echo "💡 빌드 작업은 다음과 같이 병렬화 가능:"
                echo "   • 프론트엔드 빌드"
                echo "   • 백엔드 빌드"
                echo "   • Docker 이미지 빌드"
                echo "   • 문서 생성"
                ;;
        esac
    else
        echo "⚠️ 병렬 처리가 비활성화되어 있습니다."
        echo "   ENABLE_PARALLEL=true로 설정하여 성능을 향상시킬 수 있습니다."
    fi
}

# 워크플로우 성능 분석
analyze_workflow_performance() {
    echo ""
    echo "📈 워크플로우 성능 분석..."
    
    # 체크포인트 기록에서 단계별 실행 시간 분석
    local checkpoint_file="$HOME/.claude/.workflow-state.json"
    if [ -f "$checkpoint_file" ]; then
        echo "⏱️ 단계별 실행 시간 분석:"
        
        # 완료된 단계들의 평균 실행 시간 계산
        local completed_stages=$(jq -r '.[] | select(.status == "completed") | .stage' "$checkpoint_file" 2>/dev/null | sort | uniq)
        
        while IFS= read -r stage; do
            if [ -n "$stage" ]; then
                local stage_times=$(jq -r --arg stage "$stage" '.[] | select(.stage == $stage and .status == "completed") | .timestamp' "$checkpoint_file" 2>/dev/null)
                local count=$(echo "$stage_times" | wc -l)
                echo "   📊 $stage: 평균 실행 횟수 $count회"
            fi
        done <<< "$completed_stages"
        
        # 가장 시간이 오래 걸리는 단계 식별
        echo ""
        echo "🐌 성능 개선이 필요한 영역:"
        echo "   • 파일명 검증: 대량 파일 처리 시 시간 소요"
        echo "   • CI/CD 검증: 외부 API 호출로 인한 지연"
        echo "   • Agent 실행: Python 프로세스 시작 오버헤드"
        
    else
        echo "⚠️ 성능 분석을 위한 체크포인트 데이터가 없습니다."
    fi
}

# 리소스 사용량 최적화
optimize_resource_usage() {
    echo ""
    echo "💾 리소스 사용량 최적화..."
    
    # 메모리 사용량 확인
    local mem_usage=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')
    echo "📊 현재 메모리 사용률: $mem_usage"
    
    # 디스크 사용량 확인
    local disk_usage=$(df -h . | awk 'NR==2{print $5}' | sed 's/%//')
    echo "💿 현재 디스크 사용률: ${disk_usage}%"
    
    if [ "$disk_usage" -gt 80 ]; then
        echo "⚠️ 디스크 사용률이 높습니다. 정리가 필요합니다."
        echo "   정리 권장 항목:"
        echo "   • 오래된 체크포인트 파일"
        echo "   • 병렬 실행 결과 파일"
        echo "   • 백업 파일"
        
        # 자동 정리 제안
        echo ""
        echo "자동 정리를 실행하시겠습니까? (y/n)"
        if [ "${AUTO_APPROVE:-false}" = "true" ]; then
            echo "🤖 자동 승인으로 정리 실행"
            cleanup_old_files
        else
            read -r cleanup_choice
            if [ "$cleanup_choice" = "y" ] || [ "$cleanup_choice" = "Y" ]; then
                cleanup_old_files
            fi
        fi
    fi
    
    # CPU 코어 수에 따른 병렬 처리 최적화
    local cpu_cores=$(nproc)
    echo "🖥️ 사용 가능한 CPU 코어: $cpu_cores개"
    
    if [ "$cpu_cores" -ge 4 ]; then
        echo "✅ 병렬 처리에 적합한 환경입니다."
        echo "   권장 병렬 작업 수: $((cpu_cores / 2))"
    else
        echo "⚠️ CPU 코어가 적습니다. 병렬 처리 시 주의가 필요합니다."
    fi
}

# 오래된 파일 정리
cleanup_old_files() {
    echo "🗑️ 오래된 파일 정리 중..."
    
    local cleaned_count=0
    
    # 7일 이상 된 체크포인트 백업 파일 정리
    if [ -d "$HOME/.claude/.checkpoints" ]; then
        local old_checkpoints=$(find "$HOME/.claude/.checkpoints" -name "*.json" -mtime +7 2>/dev/null | wc -l)
        if [ "$old_checkpoints" -gt 0 ]; then
            find "$HOME/.claude/.checkpoints" -name "*.json" -mtime +7 -delete 2>/dev/null || true
            cleaned_count=$((cleaned_count + old_checkpoints))
            echo "   ✅ 오래된 체크포인트 $old_checkpoints개 정리"
        fi
    fi
    
    # 오래된 병렬 실행 결과 파일 정리
    if [ -d "$HOME/.claude/.parallel-results" ]; then
        local old_results=$(find "$HOME/.claude/.parallel-results" -name "*.result" -mtime +3 2>/dev/null | wc -l)
        if [ "$old_results" -gt 0 ]; then
            find "$HOME/.claude/.parallel-results" -name "*.result" -mtime +3 -delete 2>/dev/null || true
            find "$HOME/.claude/.parallel-results" -name "*.log" -mtime +3 -delete 2>/dev/null || true
            cleaned_count=$((cleaned_count + old_results))
            echo "   ✅ 오래된 병렬 실행 결과 $old_results개 정리"
        fi
    fi
    
    # 임시 파일 정리
    local temp_files=$(find /tmp -name "*claude*" -mtime +1 2>/dev/null | wc -l)
    if [ "$temp_files" -gt 0 ]; then
        find /tmp -name "*claude*" -mtime +1 -delete 2>/dev/null || true
        cleaned_count=$((cleaned_count + temp_files))
        echo "   ✅ 임시 파일 $temp_files개 정리"
    fi
    
    echo "🎉 총 $cleaned_count개 파일 정리 완료"
}

# 최적화 권장사항 제공
provide_optimization_recommendations() {
    echo ""
    echo "💡 워크플로우 최적화 권장사항:"
    echo "================================"
    echo ""
    echo "1. 🔀 병렬 처리 활용"
    echo "   export ENABLE_PARALLEL=true"
    echo ""
    echo "2. ⚡ 자동 승인 모드"
    echo "   export AUTO_APPROVE=true"
    echo ""
    echo "3. 🎯 선택적 실행"
    echo "   특정 워크플로우만 실행하여 시간 절약"
    echo ""
    echo "4. 📍 체크포인트 활용"
    echo "   실패 시 처음부터 다시 시작하지 말고 체크포인트에서 재시작"
    echo ""
    echo "5. 🧹 정기적인 정리"
    echo "   주기적으로 오래된 파일들을 정리하여 성능 유지"
}

# 메인 실행
main() {
    local task="$1"
    
    optimize_workflow "$task"
    provide_optimization_recommendations
    
    echo ""
    echo "✅ Workflow Optimizer Agent 작업 완료"
}

# 인자가 제공되지 않은 경우 기본 동작
if [ $# -eq 0 ]; then
    echo "⚠️ 작업이 지정되지 않았습니다."
    echo "기본 워크플로우 최적화 분석을 실행합니다."
    main "워크플로우 최적화"
else
    main "$1"
fi