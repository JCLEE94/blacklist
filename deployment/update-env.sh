#!/bin/bash

# 환경 변수 업데이트 스크립트
# 사용법: ./update-env.sh [변수명] [값]

ENV_FILE=".env.production"

if [ $# -eq 0 ]; then
    echo "현재 환경 변수:"
    cat $ENV_FILE
    exit 0
fi

if [ $# -eq 1 ]; then
    echo "현재 값:"
    grep "^$1=" $ENV_FILE
    exit 0
fi

if [ $# -eq 2 ]; then
    # 백업 생성
    cp $ENV_FILE ${ENV_FILE}.backup

    # 변수 업데이트
    if grep -q "^$1=" $ENV_FILE; then
        sed -i "s|^$1=.*|$1=$2|" $ENV_FILE
        echo "✅ $1 업데이트 완료"
    else
        echo "$1=$2" >> $ENV_FILE
        echo "✅ $1 추가 완료"
    fi

    # 서비스 재시작
    echo "🔄 서비스 재시작 중..."
    docker-compose restart blacklist-app
fi