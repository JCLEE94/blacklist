#!/bin/bash
# Environment Switching Script for Blacklist Docker Optimization
# Version: v1.0.37

set -euo pipefail

ENVS=("production" "development" "local")
CURRENT_ENV=""

# 현재 환경 확인
check_current_env() {
    if [[ -L ".env" ]]; then
        CURRENT_ENV=$(readlink .env | sed 's/\.env\.//')
    elif [[ -f ".env" ]]; then
        CURRENT_ENV="커스텀 (.env 파일)"
    else
        CURRENT_ENV="없음"
    fi
}

# 사용법 출력
show_usage() {
    echo "🔧 Blacklist 환경 전환 도구"
    echo ""
    echo "사용법: $0 [환경]"
    echo ""
    echo "사용 가능한 환경:"
    echo "  production  - 운영 환경 (32542 포트, PostgreSQL, 수집 활성화)"
    echo "  development - 개발 환경 (2542 포트, 디버그 모드, 수집 비활성화)"
    echo "  local      - 로컬 환경 (2542 포트, SQLite, 보안 비활성화)"
    echo ""
    check_current_env
    echo "현재 환경: $CURRENT_ENV"
    echo ""
    echo "예시:"
    echo "  $0 production   # 운영 환경으로 전환"
    echo "  $0 development  # 개발 환경으로 전환"
    echo "  $0 local        # 로컬 환경으로 전환"
}

# 환경별 설정 정보 출력
show_env_info() {
    local env=$1
    
    case $env in
        "production")
            echo "🏭 운영 환경 설정:"
            echo "  - 포트: 32542 (외부) → 2542 (내부)"
            echo "  - 데이터베이스: PostgreSQL"
            echo "  - 캐시: Redis (1GB)"
            echo "  - 수집: 활성화"
            echo "  - 보안: 전체 활성화"
            echo "  - 로그 레벨: WARNING"
            echo "  - Watchtower: 활성화 (5분 간격)"
            ;;
        "development")
            echo "🛠️  개발 환경 설정:"
            echo "  - 포트: 2542"
            echo "  - 데이터베이스: PostgreSQL (개발용)"
            echo "  - 캐시: Redis (256MB)"
            echo "  - 수집: 비활성화 (안전)"
            echo "  - 보안: 부분 활성화"
            echo "  - 로그 레벨: DEBUG"
            echo "  - Watchtower: 비활성화"
            ;;
        "local")
            echo "💻 로컬 환경 설정:"
            echo "  - 포트: 2542"
            echo "  - 데이터베이스: PostgreSQL (로컬)"
            echo "  - 캐시: Redis (128MB)"
            echo "  - 수집: 완전 비활성화"
            echo "  - 보안: 비활성화"
            echo "  - 로그 레벨: DEBUG"
            echo "  - 인증: 비활성화"
            ;;
    esac
}

# 환경 전환 실행
switch_environment() {
    local target_env=$1
    
    if [[ ! -f ".env.$target_env" ]]; then
        echo "❌ 환경 파일이 존재하지 않습니다: .env.$target_env"
        exit 1
    fi
    
    check_current_env
    
    echo "🔄 환경 전환: $CURRENT_ENV → $target_env"
    echo ""
    
    show_env_info "$target_env"
    echo ""
    
    # 현재 실행 중인 서비스 확인
    if docker-compose ps | grep -q "Up"; then
        echo "⚠️  현재 Docker 서비스가 실행 중입니다."
        echo "환경 전환을 위해 서비스를 재시작해야 합니다."
        echo ""
        read -p "서비스를 중지하고 새 환경으로 시작하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🛑 서비스 중지 중..."
            docker-compose down
            echo "✅ 서비스 중지 완료"
        else
            echo "❌ 환경 전환이 취소되었습니다."
            exit 1
        fi
    fi
    
    # 환경 파일 전환
    echo "🔧 환경 파일 전환 중..."
    rm -f .env
    ln -s ".env.$target_env" .env
    
    echo "✅ 환경 전환 완료: $target_env"
    echo ""
    
    # 환경별 추가 설정
    case $target_env in
        "production")
            echo "🔥 운영 환경 시작 준비:"
            echo "  docker-compose --profile watchtower up -d"
            ;;
        "development"|"local")
            echo "🛠️  개발 환경 시작 준비:"
            echo "  docker-compose up -d"
            ;;
    esac
    
    echo ""
    echo "📋 다음 단계:"
    echo "  1. 볼륨 정리 (선택): ./scripts/cleanup-volumes.sh"
    echo "  2. 서비스 시작: docker-compose up -d"
    echo "  3. 상태 확인: docker-compose ps"
    echo "  4. 로그 확인: docker-compose logs -f blacklist"
}

# 메인 로직
main() {
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 0
    fi
    
    local target_env=$1
    
    # 환경 유효성 확인
    if [[ ! " ${ENVS[*]} " =~ " ${target_env} " ]]; then
        echo "❌ 잘못된 환경: $target_env"
        echo ""
        show_usage
        exit 1
    fi
    
    switch_environment "$target_env"
}

# 스크립트 실행
main "$@"