#!/bin/bash
: '
# 🤖 Requirements Manager Agent
# 사용자 요구사항 관리 및 추적 전문 Agent
'

set -euo pipefail

echo "🤖 Requirements Manager Agent 실행 중..."
echo "작업: $1"

REQUIREMENTS_TRACKER="$HOME/.claude/commands/utils/requirements-tracker.md"

# 요구사항 관리 로직
manage_requirements() {
    local task="$1"
    
    echo "📋 요구사항 관리 작업 분석 중..."
    
    case "$task" in
        *"요구사항"*|*"추가"*|*"개선"*|*"수정"*)
            echo "🔍 사용자 요구사항으로 분류됨"
            
            # 요구사항 추출 및 등록
            if [ -x "$REQUIREMENTS_TRACKER" ]; then
                echo "📝 요구사항 자동 등록 중..."
                
                # 우선순위 결정 로직
                local priority="medium"
                if [[ "$task" == *"긴급"* ]] || [[ "$task" == *"urgent"* ]]; then
                    priority="high"
                elif [[ "$task" == *"나중에"* ]] || [[ "$task" == *"언젠가"* ]]; then
                    priority="low"
                fi
                
                # 카테고리 결정
                local category="general"
                if [[ "$task" == *"UI"* ]] || [[ "$task" == *"인터페이스"* ]]; then
                    category="ui"
                elif [[ "$task" == *"성능"* ]] || [[ "$task" == *"최적화"* ]]; then
                    category="performance"
                elif [[ "$task" == *"보안"* ]] || [[ "$task" == *"권한"* ]]; then
                    category="security"
                elif [[ "$task" == *"테스트"* ]] || [[ "$task" == *"검증"* ]]; then
                    category="testing"
                elif [[ "$task" == *"배포"* ]] || [[ "$task" == *"인프라"* ]]; then
                    category="infrastructure"
                fi
                
                # 요구사항 등록
                "$REQUIREMENTS_TRACKER" add "$task" "$priority" "$category" "agent_auto"
                
                echo "✅ 요구사항이 자동으로 등록되었습니다."
                echo "   우선순위: $priority"
                echo "   카테고리: $category"
            else
                echo "⚠️ Requirements Tracker를 찾을 수 없습니다."
            fi
            ;;
        *"상태"*|*"진행"*|*"확인"*)
            echo "📊 요구사항 상태 확인"
            
            if [ -x "$REQUIREMENTS_TRACKER" ]; then
                echo ""
                echo "현재 요구사항 상태:"
                "$REQUIREMENTS_TRACKER" list
            fi
            ;;
        *"완료"*|*"끝"*|*"마침"*)
            echo "🎉 요구사항 완료 처리"
            
            if [ -x "$REQUIREMENTS_TRACKER" ]; then
                echo "최근 진행 중인 요구사항을 완료로 표시합니다..."
                # TODO: 자동으로 최근 in_progress 요구사항을 completed로 변경
            fi
            ;;
        *)
            echo "🤔 일반적인 작업으로 분류됨"
            echo "   요구사항 추적 대상 아님"
            ;;
    esac
}

# 요구사항 분석 및 우선순위 제안
analyze_requirements() {
    echo ""
    echo "🧠 요구사항 분석 및 우선순위 제안..."
    
    if [ -x "$REQUIREMENTS_TRACKER" ]; then
        # 고우선순위 요구사항 확인
        local high_priority_count=$("$REQUIREMENTS_TRACKER" list pending high | grep -c "HIGH" 2>/dev/null || echo "0")
        local total_pending=$("$REQUIREMENTS_TRACKER" list pending | grep -c "PENDING" 2>/dev/null || echo "0")
        
        if [ "$high_priority_count" -gt 0 ]; then
            echo "⚡ 고우선순위 요구사항 $high_priority_count개 발견!"
            echo "   즉시 처리를 권장합니다."
        fi
        
        if [ "$total_pending" -gt 10 ]; then
            echo "📈 대기 중인 요구사항이 많습니다 ($total_pending개)"
            echo "   우선순위 재조정을 권장합니다."
        fi
        
        # 완료율 계산
        local completed_count=$("$REQUIREMENTS_TRACKER" list completed | grep -c "COMPLETED" 2>/dev/null || echo "0")
        local total_count=$("$REQUIREMENTS_TRACKER" list | grep -c "\[.*\]" 2>/dev/null || echo "0")
        
        if [ "$total_count" -gt 0 ]; then
            local completion_rate=$((completed_count * 100 / total_count))
            echo "📊 전체 완료율: $completion_rate% ($completed_count/$total_count)"
            
            if [ "$completion_rate" -lt 50 ]; then
                echo "⚠️ 완료율이 낮습니다. 집중적인 작업이 필요합니다."
            elif [ "$completion_rate" -gt 80 ]; then
                echo "🎉 완료율이 높습니다! 좋은 진행 상황입니다."
            fi
        fi
    fi
}

# 메인 실행
main() {
    local task="$1"
    
    manage_requirements "$task"
    analyze_requirements
    
    echo ""
    echo "✅ Requirements Manager Agent 작업 완료"
}

# 인자가 제공되지 않은 경우 기본 동작
if [ $# -eq 0 ]; then
    echo "⚠️ 작업이 지정되지 않았습니다."
    echo "기본 요구사항 상태 확인을 실행합니다."
    main "상태 확인"
else
    main "$1"
fi