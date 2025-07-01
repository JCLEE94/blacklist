#!/bin/bash
# 이미지 업데이트 자동 감지 및 배포 스크립트

echo "🔄 이미지 업데이트 감지 시작..."

# 설정
NAMESPACE="blacklist"
REGISTRY="registry.jclee.me"
IMAGE_NAME="blacklist"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"  # 60초마다 체크

# 현재 배포된 이미지 태그 가져오기
get_current_image() {
    kubectl get deployment blacklist -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null
}

# Registry에서 최신 이미지 태그 가져오기  
get_latest_image_tag() {
    # Docker Registry API v2 사용
    local registry_url="https://$REGISTRY/v2/$IMAGE_NAME/tags/list"
    local auth_header=""
    
    # 기본 인증이 필요한 경우
    if [ -n "$REGISTRY_USER" ] && [ -n "$REGISTRY_PASS" ]; then
        local auth_string=$(echo -n "$REGISTRY_USER:$REGISTRY_PASS" | base64)
        auth_header="-H Authorization: Basic $auth_string"
    fi
    
    # 최신 태그 가져오기 (latest 제외하고 SHA 기반 태그 중 최신)
    curl -s $auth_header "$registry_url" | \
        jq -r '.tags[]' | \
        grep -E '^[a-f0-9]{8}$' | \
        sort | \
        tail -1
}

# 이미지 업데이트 실행
update_image() {
    local new_tag=$1
    local new_image="$REGISTRY/$IMAGE_NAME:$new_tag"
    
    echo "🔄 이미지 업데이트 중: $new_image"
    
    # 이미지 업데이트
    kubectl set image deployment/blacklist \
        blacklist="$new_image" \
        -n $NAMESPACE
    
    # 롤아웃 상태 확인
    if kubectl rollout status deployment/blacklist -n $NAMESPACE --timeout=300s; then
        echo "✅ 이미지 업데이트 성공: $new_image"
        
        # 간단한 헬스 체크
        sleep 10
        NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
        NODE_PORT=$(kubectl get svc blacklist -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "32541")
        
        if curl -f -s --max-time 10 "http://$NODE_IP:$NODE_PORT/health" > /dev/null 2>&1; then
            echo "✅ 헬스 체크 통과"
            
            # 슬랙 알림 (선택사항)
            if [ -n "$SLACK_WEBHOOK_URL" ]; then
                curl -X POST "$SLACK_WEBHOOK_URL" \
                    -H 'Content-type: application/json' \
                    --data '{
                        "text": "🚀 Blacklist 자동 업데이트 완료",
                        "attachments": [{
                            "color": "good",
                            "fields": [{
                                "title": "새 이미지",
                                "value": "'$new_image'",
                                "short": true
                            }, {
                                "title": "네임스페이스", 
                                "value": "'$NAMESPACE'",
                                "short": true
                            }]
                        }]
                    }' 2>/dev/null || echo "슬랙 알림 실패 (선택사항)"
            fi
        else
            echo "⚠️ 헬스 체크 실패 - 롤백 고려"
        fi
    else
        echo "❌ 이미지 업데이트 실패"
        return 1
    fi
}

# 메인 루프
echo "📊 모니터링 설정:"
echo "   - 네임스페이스: $NAMESPACE"
echo "   - 이미지: $REGISTRY/$IMAGE_NAME"
echo "   - 체크 간격: ${CHECK_INTERVAL}초"
echo ""

while true; do
    echo "🔍 $(date '+%Y-%m-%d %H:%M:%S') - 이미지 체크 중..."
    
    # 현재 배포된 이미지
    current_image=$(get_current_image)
    if [ -z "$current_image" ]; then
        echo "❌ 현재 배포 정보를 가져올 수 없음"
        sleep $CHECK_INTERVAL
        continue
    fi
    
    current_tag=$(echo "$current_image" | cut -d':' -f2)
    echo "   현재 이미지: $current_image"
    
    # Registry에서 최신 태그 확인
    latest_tag=$(get_latest_image_tag)
    if [ -z "$latest_tag" ]; then
        echo "⚠️ Registry에서 최신 태그를 가져올 수 없음"
        sleep $CHECK_INTERVAL
        continue
    fi
    
    echo "   최신 태그: $latest_tag"
    
    # 태그 비교
    if [ "$current_tag" != "$latest_tag" ] && [ "$current_tag" != "latest" ]; then
        echo "🆕 새로운 이미지 발견: $latest_tag"
        update_image "$latest_tag"
    else
        echo "✅ 이미지가 최신 상태"
    fi
    
    echo "⏳ ${CHECK_INTERVAL}초 대기..."
    sleep $CHECK_INTERVAL
done