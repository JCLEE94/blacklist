#!/bin/bash
# 도커 볼륨 구조 생성 스크립트

echo "📁 도커 볼륨 구조 생성"
echo "======================"
echo ""

echo "운영 서버에서 실행할 명령:"
echo ""

echo "# 1. 디렉토리 구조 생성"
echo "sudo mkdir -p /opt/blacklist/instance"
echo "sudo mkdir -p /opt/blacklist/data"
echo "sudo mkdir -p /opt/blacklist/logs"
echo "sudo mkdir -p /opt/blacklist/config"
echo ""

echo "# 2. 권한 설정 (Docker 컨테이너 내부 UID 1000에 맞춤)"
echo "sudo chown -R 1000:1000 /opt/blacklist/"
echo "sudo chmod -R 755 /opt/blacklist/"
echo ""

echo "# 3. 초기 파일 생성"
echo "sudo touch /opt/blacklist/logs/app.log"
echo "sudo touch /opt/blacklist/logs/error.log"
echo "sudo touch /opt/blacklist/instance/.gitkeep"
echo "sudo touch /opt/blacklist/data/.gitkeep"
echo ""

echo "# 4. 권한 재확인"
echo "sudo chown -R 1000:1000 /opt/blacklist/"
echo ""

echo "# 5. 구조 확인"
echo "tree /opt/blacklist/ || ls -la /opt/blacklist/"
echo ""

echo "# 6. 디스크 사용량 확인"
echo "df -h /opt/"
echo ""

echo "생성될 디렉토리 구조:"
echo "/opt/blacklist/"
echo "├── instance/          # SQLite 데이터베이스, 설정 파일"
echo "│   └── blacklist.db"
echo "├── data/              # 수집된 데이터 파일"
echo "│   ├── regtech/"
echo "│   └── secudium/"
echo "├── logs/              # 애플리케이션 로그"
echo "│   ├── app.log"
echo "│   └── error.log"
echo "└── config/            # 기타 설정 파일"
echo ""

echo "볼륨 마운트 옵션:"
echo "  -v /opt/blacklist/instance:/app/instance"
echo "  -v /opt/blacklist/data:/app/data"
echo "  -v /opt/blacklist/logs:/app/logs"