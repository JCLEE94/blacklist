# 🔧 Blacklist 오프라인 배포 실행 가이드

> **실무자를 위한 단계별 실행 매뉴얼**

---

## ⚡ 빠른 실행 (15분 완성)

### 온라인 환경 (패키지 생성)
```bash
cd /home/jclee/app/blacklist
python3 scripts/create-offline-package-enhanced.py
```

### 오프라인 환경 (설치)
```bash
tar -xzf blacklist-offline-package-v2.0.tar.gz
cd blacklist-offline-package-v2.0
sudo ./install-offline.sh
```

---

## 📋 상세 실행 단계

### Phase 1: 패키지 생성 (온라인)

```bash
# 1. 프로젝트 디렉토리로 이동
cd /home/jclee/app/blacklist

# 2. 고급 패키지 빌더 실행
python3 scripts/create-offline-package-enhanced.py

# 예상 출력:
# 🚀 Starting offline package build...
# ✅ Docker images exported
# ✅ Python packages collected  
# ✅ Scripts created
# 📦 Package size: 1.5 GB
# 🎉 Build completed!
```

**생성 결과:**
- 📦 `blacklist-offline-package-v2.0.tar.gz` (약 1-2GB)
- 📄 `package-info.json` (패키지 정보)
- 🔍 SHA256 체크섬 파일

### Phase 2: 패키지 전송

```bash
# USB 복사
cp blacklist-offline-package-v2.0.tar.gz /mnt/usb/

# 네트워크 전송 (내부망)
scp blacklist-offline-package-v2.0.tar.gz user@192.168.1.100:~/

# 체크섬 검증
sha256sum blacklist-offline-package-v2.0.tar.gz
```

### Phase 3: 오프라인 설치

```bash
# 1. 패키지 압축 해제
tar -xzf blacklist-offline-package-v2.0.tar.gz
cd blacklist-offline-package-v2.0

# 2. 패키지 정보 확인
cat package-info.json | jq

# 3. 자동 설치 실행
sudo ./install-offline.sh

# 실시간 로그 확인
tail -f /var/log/blacklist-install.log
```

**설치 과정 모니터링:**
```bash
# 별도 터미널에서 모니터링
watch -n 2 "docker ps; echo '---'; df -h; echo '---'; free -h"
```

### Phase 4: 설치 검증

```bash
# 자동 검증
./verify-installation.sh

# 수동 확인
curl http://localhost:32542/health | jq
docker-compose ps
docker-compose logs blacklist
```

---

## 🔧 고급 설정 옵션

### 커스텀 포트 설정
```bash
# 포트 변경 (기본: 32542)
export BLACKLIST_PORT=8080
sudo ./install-offline.sh --port 8080
```

### 데이터베이스 설정
```bash
# PostgreSQL 사용
export USE_POSTGRES=true
export POSTGRES_PASSWORD=your_secure_password
sudo ./install-offline.sh --database postgres
```

### 리소스 제한 설정
```bash
# Docker 리소스 제한
export MEMORY_LIMIT=512m
export CPU_LIMIT=1.0
sudo ./install-offline.sh --memory 512m --cpu 1.0
```

---

## 🚨 문제 해결 시나리오

### 시나리오 1: Docker 설치 실패
```bash
# 수동 Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 또는 패키지 매니저 사용
sudo apt-get update
sudo apt-get install docker.io docker-compose
```

### 시나리오 2: 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -tulpn | grep :32542

# 프로세스 종료
sudo fuser -k 32542/tcp

# 다른 포트로 설치
sudo ./install-offline.sh --port 33542
```

### 시나리오 3: 메모리 부족
```bash
# 스왑 파일 생성 (임시 해결)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 불필요한 서비스 중지
sudo systemctl stop apache2 nginx
```

### 시나리오 4: 권한 문제
```bash
# Docker 권한 설정
sudo usermod -aG docker $USER
newgrp docker

# 디렉토리 권한 설정
sudo chown -R $USER:$USER ./blacklist-offline-package-v2.0
```

---

## 📊 성능 튜닝 가이드

### CPU 최적화
```bash
# CPU 코어 수 확인
nproc

# Gunicorn 워커 수 설정 (CPU 코어 수 × 2 + 1)
export GUNICORN_WORKERS=5
docker-compose up -d
```

### 메모리 최적화
```bash
# 메모리 사용량 모니터링
watch -n 1 "free -h; echo '---'; docker stats --no-stream"

# Redis 메모리 제한
export REDIS_MEMORY=256mb
docker-compose restart redis
```

### 네트워크 최적화
```bash
# 연결 풀 크기 조정
export DB_POOL_SIZE=20
export REDIS_POOL_SIZE=10
docker-compose restart blacklist
```

---

## 🔒 보안 강화 설정

### 1. 방화벽 설정
```bash
# UFW 활성화
sudo ufw enable

# 필수 포트만 허용
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 32542/tcp   # Blacklist API
sudo ufw deny 6379/tcp     # Redis (외부 차단)
```

### 2. SSL/TLS 설정
```bash
# 자체 서명 인증서 생성
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/blacklist.key -out ssl/blacklist.crt

# Nginx 프록시 설정
sudo ./install-offline.sh --ssl --domain your-domain.com
```

### 3. 감사 로깅 활성화
```bash
# 감사 로그 설정
export ENABLE_AUDIT_LOG=true
export AUDIT_LOG_LEVEL=INFO
docker-compose restart blacklist

# 로그 확인
tail -f logs/audit.log
```

---

## 📈 모니터링 설정

### Prometheus 메트릭
```bash
# 메트릭 엔드포인트 확인
curl http://localhost:32542/metrics

# Grafana 대시보드 (선택사항)
docker run -d -p 3000:3000 \
  -v grafana-data:/var/lib/grafana \
  grafana/grafana
```

### 로그 집중화
```bash
# 로그 수집 설정
docker run -d \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v blacklist_logs:/logs \
  fluent/fluent-bit
```

---

## 🔄 업데이트 프로세스

### 1. 새 패키지 적용
```bash
# 현재 설정 백업
cp docker-compose.yml docker-compose.yml.backup
cp -r instance/ instance.backup/

# 새 패키지 배포
tar -xzf blacklist-offline-package-v2.1.tar.gz
cd blacklist-offline-package-v2.1

# 업데이트 실행
sudo ./update-offline.sh
```

### 2. 롤백 프로세스
```bash
# 이전 버전으로 롤백
sudo ./rollback-offline.sh

# 또는 수동 롤백
docker-compose down
cp docker-compose.yml.backup docker-compose.yml
docker-compose up -d
```

---

## 📞 24시간 지원

### 긴급 상황 대응
```bash
# 시스템 상태 스냅샷 생성
./create-support-bundle.sh

# 지원 번들에 포함되는 정보:
# - 시스템 로그
# - Docker 상태
# - 네트워크 설정  
# - 리소스 사용량
# - 에러 로그
```

### 연락처
- **기술 지원**: qws941@kakao.com
- **긴급 상황**: GitHub Issues
- **문서**: https://qws941.github.io/blacklist/

---

**끝** | 실행 가이드 v2.0 | 2025-08-13