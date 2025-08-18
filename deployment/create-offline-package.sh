#!/bin/bash
# 사내망 배포를 위한 오프라인 패키지 생성 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 패키지 정보
PACKAGE_NAME="blacklist-internal-deployment"
VERSION=$(cat ../config/VERSION 2>/dev/null || echo "1.0.35")
DATE=$(date +%Y%m%d)
OUTPUT_DIR="${PACKAGE_NAME}-${VERSION}-${DATE}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}사내망 배포 패키지 생성${NC}"
echo -e "${BLUE}Version: ${VERSION}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 디렉토리 생성
echo -e "${GREEN}1. 패키지 디렉토리 생성...${NC}"
rm -rf $OUTPUT_DIR
mkdir -p $OUTPUT_DIR/{images,config,scripts,data}

# 2. Docker 이미지 저장
echo -e "${GREEN}2. Docker 이미지 저장...${NC}"
echo "   - blacklist 애플리케이션 이미지"
docker save -o $OUTPUT_DIR/images/blacklist.tar registry.jclee.me/blacklist:latest || \
docker save -o $OUTPUT_DIR/images/blacklist.tar blacklist:latest

echo "   - Redis 이미지"
docker save -o $OUTPUT_DIR/images/redis.tar redis:7-alpine

# 이미지 크기 확인
du -sh $OUTPUT_DIR/images/*.tar

# 3. 설정 파일 복사
echo -e "${GREEN}3. 설정 파일 준비...${NC}"
cp docker-compose.prod.yml $OUTPUT_DIR/docker-compose.yml

# 환경 변수 템플릿 생성
cat > $OUTPUT_DIR/config/.env.template << 'EOF'
# 사내망 배포 환경 변수 설정
# 이 파일을 .env로 복사하고 실제 값을 입력하세요

# 기본 설정
FLASK_ENV=production
PORT=2542

# 보안 키 (반드시 변경)
SECRET_KEY=change-this-to-random-string-in-production
JWT_SECRET_KEY=change-this-to-another-random-string
DEFAULT_API_KEY=blk_generate-new-api-key-here

# 관리자 계정
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-password

# 데이터 수집 설정
COLLECTION_ENABLED=true
FORCE_DISABLE_COLLECTION=false

# 외부 서비스 (사내망 URL로 변경)
REGTECH_BASE_URL=https://internal-regtech.company.local
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password

SECUDIUM_BASE_URL=https://internal-secudium.company.local
SECUDIUM_USERNAME=your-username
SECUDIUM_PASSWORD=your-password

# 로깅
LOG_LEVEL=INFO
EOF

# 4. 설치 스크립트 생성
echo -e "${GREEN}4. 설치 스크립트 생성...${NC}"
cat > $OUTPUT_DIR/install.sh << 'INSTALL_SCRIPT'
#!/bin/bash
# 사내망 Blacklist 서비스 설치 스크립트

set -e

echo "================================================"
echo "Blacklist 서비스 설치"
echo "================================================"
echo ""

# 1. Docker 확인
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker가 설치되어 있지 않습니다."
    echo "Docker를 먼저 설치해주세요."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose가 설치되어 있지 않습니다."
    exit 1
fi

# 2. 디렉토리 생성
echo "1. 설치 디렉토리 생성..."
sudo mkdir -p /opt/blacklist/{data,logs,redis}
sudo chown -R $USER:$USER /opt/blacklist

# 3. 이미지 로드
echo "2. Docker 이미지 로드..."
docker load -i images/blacklist.tar
docker load -i images/redis.tar

# 이미지 태깅
docker tag registry.jclee.me/blacklist:latest blacklist:latest 2>/dev/null || true

# 4. 환경 설정
echo "3. 환경 설정..."
if [ ! -f .env ]; then
    cp config/.env.template .env
    echo "   .env 파일이 생성되었습니다."
    echo "   필요한 설정을 수정해주세요: vi .env"
    read -p "   설정을 완료하셨습니까? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "설치를 중단합니다."
        exit 1
    fi
fi

# 5. 서비스 시작
echo "4. 서비스 시작..."
docker-compose up -d

# 6. 상태 확인
echo "5. 서비스 상태 확인..."
sleep 5
docker-compose ps

# 7. 헬스 체크
echo "6. 헬스 체크..."
sleep 5
curl -s http://localhost:32542/health | python3 -m json.tool || echo "헬스체크 실패"

echo ""
echo "================================================"
echo "설치 완료!"
echo "접속 URL: http://$(hostname -I | awk '{print $1}'):32542"
echo "================================================"
INSTALL_SCRIPT

chmod +x $OUTPUT_DIR/install.sh

# 5. 운영 스크립트 생성
echo -e "${GREEN}5. 운영 스크립트 생성...${NC}"

# 시작 스크립트
cat > $OUTPUT_DIR/scripts/start.sh << 'EOF'
#!/bin/bash
cd /opt/blacklist
docker-compose up -d
docker-compose ps
EOF

# 중지 스크립트
cat > $OUTPUT_DIR/scripts/stop.sh << 'EOF'
#!/bin/bash
cd /opt/blacklist
docker-compose down
EOF

# 재시작 스크립트
cat > $OUTPUT_DIR/scripts/restart.sh << 'EOF'
#!/bin/bash
cd /opt/blacklist
docker-compose restart
docker-compose ps
EOF

# 로그 확인 스크립트
cat > $OUTPUT_DIR/scripts/logs.sh << 'EOF'
#!/bin/bash
docker-compose logs -f --tail=100 blacklist-app
EOF

# 백업 스크립트
cat > $OUTPUT_DIR/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/blacklist/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp -r /opt/blacklist/data $BACKUP_DIR/
cp -r /opt/blacklist/redis $BACKUP_DIR/
echo "백업 완료: $BACKUP_DIR"
EOF

chmod +x $OUTPUT_DIR/scripts/*.sh

# 6. README 생성
echo -e "${GREEN}6. README 문서 생성...${NC}"
cat > $OUTPUT_DIR/README.md << 'EOF'
# Blacklist 사내망 배포 가이드

## 시스템 요구사항
- Docker 20.10 이상
- Docker Compose 1.29 이상
- 최소 2GB RAM
- 10GB 디스크 공간

## 설치 방법
1. 패키지 압축 해제
2. `./install.sh` 실행
3. `.env` 파일 수정 (필요시)
4. 브라우저에서 http://서버IP:32542 접속

## 디렉토리 구조
```
/opt/blacklist/
├── data/      # SQLite 데이터베이스
├── logs/      # 애플리케이션 로그
└── redis/     # Redis 데이터
```

## 운영 명령어
- 시작: `./scripts/start.sh`
- 중지: `./scripts/stop.sh`
- 재시작: `./scripts/restart.sh`
- 로그 확인: `./scripts/logs.sh`
- 백업: `./scripts/backup.sh`

## 포트 정보
- 32542: Blacklist 웹 서비스

## 문제 해결
- 서비스 상태 확인: `docker-compose ps`
- 헬스 체크: `curl http://localhost:32542/health`
- 컨테이너 로그: `docker logs blacklist-app`
EOF

# 7. 패키지 압축
echo -e "${GREEN}7. 패키지 압축...${NC}"
tar -czf ${OUTPUT_DIR}.tar.gz $OUTPUT_DIR/
PACKAGE_SIZE=$(du -sh ${OUTPUT_DIR}.tar.gz | cut -f1)

# 8. 완료
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 패키지 생성 완료!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📦 패키지 파일: ${OUTPUT_DIR}.tar.gz"
echo "📏 패키지 크기: $PACKAGE_SIZE"
echo ""
echo "🚀 배포 방법:"
echo "1. 패키지를 사내망 서버로 복사"
echo "2. tar -xzf ${OUTPUT_DIR}.tar.gz"
echo "3. cd ${OUTPUT_DIR}"
echo "4. ./install.sh"
echo ""