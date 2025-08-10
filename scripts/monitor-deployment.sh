#!/bin/bash
# 실시간 배포 상태 모니터링

echo "🚀 Watchtower 배포 실시간 모니터링"
echo "================================="

start_time=$(date +%s)
max_wait=600  # 10분 최대 대기

echo "⏰ 시작 시간: $(date)"
echo "🎯 대상: http://192.168.50.215:30001"
echo ""

while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    if [ $elapsed -gt $max_wait ]; then
        echo "❌ 타임아웃: 10분 초과, 수동 개입 필요"
        break
    fi
    
    # 서비스 응답 테스트
    if curl -s --connect-timeout 3 http://192.168.50.215:30001/health >/dev/null 2>&1; then
        echo "✅ $(date +'%H:%M:%S') - 서비스 정상 응답! (경과: ${elapsed}초)"
        
        # 버전 정보 확인
        version=$(curl -s http://192.168.50.215:30001/health | jq -r '.version // "unknown"' 2>/dev/null)
        echo "📦 현재 버전: $version"
        break
    else
        echo "⏳ $(date +'%H:%M:%S') - 대기 중... (경과: ${elapsed}초)"
    fi
    
    sleep 10
done

echo ""
echo "🏁 모니터링 완료"