#!/bin/bash
# 도커 볼륨 마운트 상태 확인 스크립트

echo "🔍 도커 볼륨 마운트 상태 확인"
echo "================================"
echo ""
echo "운영 서버에서 실행할 명령:"
echo ""

echo "# 1. 현재 실행 중인 컨테이너와 볼륨 확인"
echo "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Mounts}}'"
echo ""

echo "# 2. 상세 볼륨 정보"
echo "docker inspect blacklist-app | grep -A 10 -B 5 Mounts"
echo ""

echo "# 3. 호스트 디렉토리 확인"
echo "ls -la /opt/blacklist/"
echo "ls -la /opt/blacklist/instance/"
echo "ls -la /opt/blacklist/data/"
echo "ls -la /opt/blacklist/logs/"
echo ""

echo "# 4. 컨테이너 내부 확인"
echo "docker exec blacklist-app ls -la /app/"
echo "docker exec blacklist-app ls -la /app/instance/"
echo "docker exec blacklist-app ls -la /app/data/"
echo "docker exec blacklist-app ls -la /app/logs/"
echo ""

echo "# 5. 데이터베이스 파일 확인"
echo "docker exec blacklist-app ls -la /app/instance/blacklist.db"
echo "ls -la /opt/blacklist/instance/blacklist.db"
echo ""

echo "# 6. 볼륨 사용량 확인"
echo "df -h /opt/blacklist/"
echo "du -sh /opt/blacklist/*"
echo ""

echo "# 7. 도커 볼륨 리스트"
echo "docker volume ls | grep blacklist"
echo ""

echo "# 8. 권한 확인"
echo "stat /opt/blacklist/instance/"
echo "docker exec blacklist-app stat /app/instance/"
echo ""

echo "현재 설정된 볼륨 마운트:"
echo "  - /opt/blacklist/instance:/app/instance (데이터베이스)"
echo "  - /opt/blacklist/data:/app/data (수집 데이터)"
echo "  - /opt/blacklist/logs:/app/logs (로그 파일)"