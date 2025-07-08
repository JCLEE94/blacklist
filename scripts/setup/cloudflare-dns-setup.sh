#!/bin/bash
# Cloudflare DNS 자동 설정 스크립트

echo "🌐 Cloudflare DNS 설정 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Cloudflare API 설정
CF_API_TOKEN="${CF_API_TOKEN:-19OuO8pBp83XDkJsUf2TRmDPKd6ZySIXrGJbh5Uk}"
CF_API_URL="https://api.cloudflare.com/client/v4"

# 기본값 설정
DOMAIN="${DOMAIN:-jclee.me}"
SUBDOMAIN="${SUBDOMAIN:-blacklist}"
TUNNEL_ID="${TUNNEL_ID:-}"
RECORD_TYPE="${RECORD_TYPE:-CNAME}"

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Zone ID 가져오기
get_zone_id() {
    print_step "Zone ID 조회 중..."
    
    ZONE_RESPONSE=$(curl -s -X GET "$CF_API_URL/zones?name=$DOMAIN" \
        -H "Authorization: Bearer $CF_API_TOKEN" \
        -H "Content-Type: application/json")
    
    ZONE_ID=$(echo "$ZONE_RESPONSE" | jq -r '.result[0].id')
    
    if [ "$ZONE_ID" = "null" ] || [ -z "$ZONE_ID" ]; then
        print_error "Zone ID를 찾을 수 없습니다. 도메인: $DOMAIN"
        echo "응답: $ZONE_RESPONSE"
        return 1
    fi
    
    print_success "Zone ID 조회 완료: $ZONE_ID"
    export ZONE_ID
    return 0
}

# 기존 DNS 레코드 확인
check_existing_record() {
    local record_name="$1"
    
    print_step "기존 DNS 레코드 확인 중: $record_name"
    
    RECORD_RESPONSE=$(curl -s -X GET "$CF_API_URL/zones/$ZONE_ID/dns_records?name=$record_name" \
        -H "Authorization: Bearer $CF_API_TOKEN" \
        -H "Content-Type: application/json")
    
    RECORD_ID=$(echo "$RECORD_RESPONSE" | jq -r '.result[0].id')
    
    if [ "$RECORD_ID" != "null" ] && [ -n "$RECORD_ID" ]; then
        print_warning "기존 레코드 발견: $record_name (ID: $RECORD_ID)"
        return 0
    else
        print_step "새로운 레코드를 생성합니다: $record_name"
        return 1
    fi
}

# DNS 레코드 생성
create_dns_record() {
    local record_name="$1"
    local record_content="$2"
    local record_type="${3:-CNAME}"
    local proxied="${4:-true}"
    
    print_step "DNS 레코드 생성 중: $record_name"
    
    # 기존 레코드 확인
    if check_existing_record "$record_name"; then
        print_step "기존 레코드 업데이트 중..."
        
        # 레코드 업데이트
        UPDATE_RESPONSE=$(curl -s -X PUT "$CF_API_URL/zones/$ZONE_ID/dns_records/$RECORD_ID" \
            -H "Authorization: Bearer $CF_API_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
                \"type\": \"$record_type\",
                \"name\": \"$record_name\",
                \"content\": \"$record_content\",
                \"proxied\": $proxied
            }")
        
        SUCCESS=$(echo "$UPDATE_RESPONSE" | jq -r '.success')
        
        if [ "$SUCCESS" = "true" ]; then
            print_success "DNS 레코드 업데이트 완료: $record_name"
            return 0
        else
            print_error "DNS 레코드 업데이트 실패"
            echo "응답: $UPDATE_RESPONSE"
            return 1
        fi
    else
        # 새 레코드 생성
        CREATE_RESPONSE=$(curl -s -X POST "$CF_API_URL/zones/$ZONE_ID/dns_records" \
            -H "Authorization: Bearer $CF_API_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
                \"type\": \"$record_type\",
                \"name\": \"$record_name\",
                \"content\": \"$record_content\",
                \"proxied\": $proxied
            }")
        
        SUCCESS=$(echo "$CREATE_RESPONSE" | jq -r '.success')
        
        if [ "$SUCCESS" = "true" ]; then
            print_success "DNS 레코드 생성 완료: $record_name"
            return 0
        else
            print_error "DNS 레코드 생성 실패"
            echo "응답: $CREATE_RESPONSE"
            return 1
        fi
    fi
}

# Cloudflare Tunnel 정보 가져오기
get_tunnel_info() {
    print_step "Cloudflare Tunnel 정보 조회 중..."
    
    # 모든 터널 조회
    TUNNELS_RESPONSE=$(curl -s -X GET "$CF_API_URL/accounts/$ACCOUNT_ID/cfd_tunnel" \
        -H "Authorization: Bearer $CF_API_TOKEN" \
        -H "Content-Type: application/json")
    
    # blacklist 터널 찾기
    TUNNEL_INFO=$(echo "$TUNNELS_RESPONSE" | jq -r '.result[] | select(.name | contains("blacklist"))')
    
    if [ -n "$TUNNEL_INFO" ]; then
        TUNNEL_ID=$(echo "$TUNNEL_INFO" | jq -r '.id')
        TUNNEL_NAME=$(echo "$TUNNEL_INFO" | jq -r '.name')
        print_success "터널 발견: $TUNNEL_NAME (ID: $TUNNEL_ID)"
        export TUNNEL_ID
        return 0
    else
        print_warning "blacklist 터널을 찾을 수 없습니다."
        return 1
    fi
}

# 계정 ID 가져오기
get_account_id() {
    print_step "Cloudflare 계정 정보 조회 중..."
    
    ACCOUNT_RESPONSE=$(curl -s -X GET "$CF_API_URL/user/tokens/verify" \
        -H "Authorization: Bearer $CF_API_TOKEN" \
        -H "Content-Type: application/json")
    
    # 계정 목록 가져오기
    ACCOUNTS_RESPONSE=$(curl -s -X GET "$CF_API_URL/accounts" \
        -H "Authorization: Bearer $CF_API_TOKEN" \
        -H "Content-Type: application/json")
    
    ACCOUNT_ID=$(echo "$ACCOUNTS_RESPONSE" | jq -r '.result[0].id')
    
    if [ "$ACCOUNT_ID" = "null" ] || [ -z "$ACCOUNT_ID" ]; then
        print_error "계정 ID를 찾을 수 없습니다."
        return 1
    fi
    
    print_success "계정 ID 조회 완료: $ACCOUNT_ID"
    export ACCOUNT_ID
    return 0
}

# Cloudflare Tunnel 라우트 설정
setup_tunnel_route() {
    local hostname="$1"
    local service="$2"
    
    print_step "터널 라우트 설정 중: $hostname -> $service"
    
    # 터널 설정 업데이트
    CONFIG_RESPONSE=$(curl -s -X PUT "$CF_API_URL/accounts/$ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/configurations" \
        -H "Authorization: Bearer $CF_API_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"config\": {
                \"ingress\": [
                    {
                        \"hostname\": \"$hostname\",
                        \"service\": \"$service\"
                    },
                    {
                        \"service\": \"http_status:404\"
                    }
                ]
            }
        }")
    
    SUCCESS=$(echo "$CONFIG_RESPONSE" | jq -r '.success')
    
    if [ "$SUCCESS" = "true" ]; then
        print_success "터널 라우트 설정 완료"
        return 0
    else
        print_warning "터널 라우트 설정 실패 (터널이 실행 중일 수 있음)"
        return 1
    fi
}

# 메인 실행
main() {
    echo "======================================"
    echo "Cloudflare DNS 자동 설정"
    echo "======================================"
    echo ""
    echo "설정:"
    echo "  도메인: $DOMAIN"
    echo "  서브도메인: $SUBDOMAIN"
    echo "  전체 호스트명: $SUBDOMAIN.$DOMAIN"
    echo ""
    
    # 1. Zone ID 가져오기
    if ! get_zone_id; then
        print_error "Zone ID 조회 실패"
        exit 1
    fi
    
    # 2. 계정 ID 가져오기
    if ! get_account_id; then
        print_error "계정 ID 조회 실패"
        exit 1
    fi
    
    # 3. 터널 정보 가져오기 (선택적)
    if get_tunnel_info; then
        # 터널이 있으면 CNAME 레코드 생성
        TUNNEL_DOMAIN="${TUNNEL_ID}.cfargotunnel.com"
        create_dns_record "$SUBDOMAIN.$DOMAIN" "$TUNNEL_DOMAIN" "CNAME" true
        
        # 터널 라우트 설정
        setup_tunnel_route "$SUBDOMAIN.$DOMAIN" "http://localhost:32452"
    else
        print_warning "터널을 찾을 수 없어 A 레코드로 생성합니다."
        
        # 현재 공인 IP 가져오기
        PUBLIC_IP=$(curl -s https://api.ipify.org)
        if [ -n "$PUBLIC_IP" ]; then
            create_dns_record "$SUBDOMAIN.$DOMAIN" "$PUBLIC_IP" "A" true
        else
            print_error "공인 IP를 가져올 수 없습니다."
            exit 1
        fi
    fi
    
    # 4. 추가 레코드 생성 (선택적)
    # www 서브도메인 추가
    if [ "$SUBDOMAIN" != "www" ]; then
        create_dns_record "www.$SUBDOMAIN.$DOMAIN" "$SUBDOMAIN.$DOMAIN" "CNAME" true
    fi
    
    echo ""
    echo "====================================="
    echo "✅ DNS 설정 완료!"
    echo "====================================="
    echo "🌐 접속 URL: https://$SUBDOMAIN.$DOMAIN"
    echo "📊 Cloudflare 대시보드: https://dash.cloudflare.com"
    echo "====================================="
}

# 명령행 인자 처리
case "${1:-setup}" in
    setup)
        main
        ;;
    list)
        get_zone_id && \
        curl -s -X GET "$CF_API_URL/zones/$ZONE_ID/dns_records" \
            -H "Authorization: Bearer $CF_API_TOKEN" \
            -H "Content-Type: application/json" | jq '.result[] | {name, type, content}'
        ;;
    delete)
        if [ -z "$2" ]; then
            print_error "삭제할 레코드 이름을 지정하세요"
            exit 1
        fi
        get_zone_id && \
        check_existing_record "$2" && \
        curl -s -X DELETE "$CF_API_URL/zones/$ZONE_ID/dns_records/$RECORD_ID" \
            -H "Authorization: Bearer $CF_API_TOKEN" \
            -H "Content-Type: application/json" | jq '.success'
        ;;
    *)
        echo "사용법: $0 [setup|list|delete <record-name>]"
        exit 1
        ;;
esac