# 블랙리스트 시스템 오프라인 배포 가이드

## 📋 개요

이 가이드는 에어갭(Air-gapped) Linux 환경에서 블랙리스트 시스템을 완전 오프라인으로 배포하는 방법을 설명합니다.

### 패키지 정보
- **패키지명**: blacklist-offline-package-v2.0
- **버전**: 2.0.0
- **지원 플랫폼**: Linux x86_64
- **패키지 크기**: 약 1-2GB (Docker 이미지 포함)

## 🎯 대상 환경

### 지원 운영체제
- Ubuntu 20.04 LTS 이상
- CentOS 8 이상
- RHEL 8 이상
- Debian 11 이상
- Amazon Linux 2

### 시스템 요구사항

| 구성요소 | 최소 사양 | 권장 사양 |
|---------|-----------|-----------|
| CPU | 2 cores | 4 cores |
| 메모리 | 4GB RAM | 8GB RAM |
| 디스크 | 20GB 여유공간 | 50GB 여유공간 |
| 네트워크 | 로컬만 | 로컬 + 외부 API (선택) |

### 사전 설치 요구사항
- **Docker 20.10+** (필수)
- **Docker Compose 1.29+** (필수)
- **Python 3.9+** (필수)
- **Git** (권장)

## 📦 패키지 구조

```
blacklist-offline-package-v2.0/
├── package-manifest.json          # 패키지 정보 및 체크섬
├── dependencies/                   # Python 의존성
│   ├── all_wheels/                # 모든 wheel 파일
│   ├── requirements-frozen.txt    # 고정된 요구사항
│   └── dependencies-info.json     # 의존성 정보
├── docker-images/                  # Docker 이미지 (tar 파일)
│   ├── registry.jclee.me_blacklist_latest.tar
│   ├── redis_7-alpine.tar
│   └── images-info.json
├── source-code/                    # 애플리케이션 소스
│   ├── src/                       # 소스 코드
│   ├── main.py                    # 메인 애플리케이션
│   ├── docker-compose.yml         # Docker Compose 설정
│   └── .env.template              # 환경변수 템플릿
├── scripts/                        # 설치 및 관리 스크립트
│   ├── install.sh                 # 메인 설치 스크립트
│   ├── load-docker-images.sh      # Docker 이미지 로드
│   ├── install-python-deps.sh     # Python 의존성 설치
│   ├── setup-systemd.sh           # systemd 서비스 설정
│   ├── health-check.sh            # 헬스체크
│   └── uninstall.sh               # 제거 스크립트
├── configs/                        # 설정 템플릿
│   ├── docker-compose.yml         # 프로덕션용 Compose
│   ├── nginx.conf                 # Nginx 설정
│   └── monitoring/                # 모니터링 설정
├── database/                       # 데이터베이스 관련
│   ├── init_database.py           # DB 초기화
│   ├── migrate.py                 # 마이그레이션
│   └── backup.sh                  # 백업 스크립트
├── docs/                          # 문서
│   ├── installation-guide.md      # 설치 가이드
│   ├── operations-guide.md        # 운영 가이드
│   ├── troubleshooting-guide.md   # 트러블슈팅
│   └── api-documentation.md       # API 문서
└── tools/                         # 검증 및 유틸리티
    ├── system-check.sh            # 시스템 요구사항 확인
    ├── verify-installation.sh     # 설치 검증
    └── performance-test.py        # 성능 테스트
```

## 🚀 설치 과정

### 1단계: 패키지 다운로드 및 압축 해제

```bash
# 패키지 다운로드 (인터넷 연결 환경에서)
wget https://releases.blacklist.jclee.me/blacklist-offline-package-v2.0.tar.gz

# 체크섬 검증
sha256sum -c blacklist-offline-package-v2.0.tar.gz.sha256

# 압축 해제
tar -xzf blacklist-offline-package-v2.0.tar.gz
cd blacklist-offline-package-v2.0
```

### 2단계: 시스템 요구사항 확인

```bash
# 시스템 요구사항 자동 확인
sudo ./tools/system-check.sh

# 수동 확인
# Docker 버전 확인
docker --version

# Python 버전 확인  
python3 --version

# 메모리 확인
free -h

# 디스크 공간 확인
df -h
```

### 3단계: 자동 설치 실행

```bash
# 루트 권한으로 설치 스크립트 실행
sudo ./scripts/install.sh

# 설치 과정 모니터링
tail -f /tmp/blacklist-install.log
```

### 4단계: 환경 설정

```bash
# 설치 디렉토리로 이동
cd /opt/blacklist

# 환경변수 파일 편집
sudo nano .env

# 필수 설정 항목:
# SECRET_KEY=your-secret-key-here
# JWT_SECRET_KEY=your-jwt-secret-here
# REGTECH_USERNAME=your-regtech-username
# REGTECH_PASSWORD=your-regtech-password
# SECUDIUM_USERNAME=your-secudium-username  
# SECUDIUM_PASSWORD=your-secudium-password
```

### 5단계: 서비스 시작

```bash
# systemd 서비스 시작
sudo systemctl start blacklist

# 서비스 상태 확인
sudo systemctl status blacklist

# 부팅 시 자동 시작 설정
sudo systemctl enable blacklist
```

### 6단계: 설치 검증

```bash
# 헬스체크 실행
./scripts/health-check.sh

# 웹 대시보드 접속
curl http://localhost:32542/health

# 브라우저에서 확인
# http://localhost:32542/dashboard
```

## ⚙️ 고급 설정

### Docker Compose 사용자 정의

```bash
# 기본 설정 복사
cd /opt/blacklist
cp configs/docker-compose.yml ./docker-compose.custom.yml

# 사용자 정의 설정 편집
nano docker-compose.custom.yml

# 사용자 정의 설정으로 재시작
docker-compose -f docker-compose.custom.yml up -d
```

### 리버스 프록시 설정 (Nginx)

```bash
# Nginx 설치 (시스템 패키지 관리자 사용)
sudo apt install nginx  # Ubuntu/Debian
sudo yum install nginx   # CentOS/RHEL

# 블랙리스트용 Nginx 설정 복사
sudo cp configs/nginx.conf /etc/nginx/sites-available/blacklist
sudo ln -s /etc/nginx/sites-available/blacklist /etc/nginx/sites-enabled/

# Nginx 재시작
sudo systemctl restart nginx
```

### SSL/TLS 설정

```bash
# 자체 서명 인증서 생성 (개발/테스트용)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/blacklist.key \
  -out /etc/ssl/certs/blacklist.crt

# Nginx SSL 설정 활성화
# (configs/nginx-ssl.conf 참조)
```

### 데이터베이스 백업 설정

```bash
# 자동 백업 스크립트 설정
sudo cp database/backup.sh /usr/local/bin/blacklist-backup
sudo chmod +x /usr/local/bin/blacklist-backup

# 일일 백업 cron 작업 추가
echo "0 2 * * * /usr/local/bin/blacklist-backup" | sudo crontab -
```

## 📊 모니터링 설정

### Prometheus 메트릭 활성화

```bash
# .env 파일에 모니터링 설정 추가
echo "PROMETHEUS_ENABLED=true" >> /opt/blacklist/.env
echo "HEALTH_DASHBOARD_ENABLED=true" >> /opt/blacklist/.env

# 서비스 재시작
sudo systemctl restart blacklist
```

### 메트릭 엔드포인트

- **Prometheus 메트릭**: `http://localhost:32542/metrics`
- **헬스 대시보드**: `http://localhost:32542/dashboard`
- **API 상태**: `http://localhost:32542/api/health`

### 알림 설정

```bash
# 알림 규칙 설정 복사
sudo cp configs/monitoring/alert-rules.yml /etc/prometheus/

# Prometheus 설정 업데이트 후 재시작
sudo systemctl restart prometheus
```

## 🔧 운영 및 유지보수

### 일상적인 관리 작업

```bash
# 서비스 상태 확인
sudo systemctl status blacklist

# 로그 확인
sudo journalctl -u blacklist -f

# Docker 컨테이너 상태 확인
cd /opt/blacklist
docker-compose ps

# 디스크 사용량 모니터링
df -h /opt/blacklist
```

### 업데이트 절차

```bash
# 1. 현재 서비스 중지
sudo systemctl stop blacklist

# 2. 데이터 백업
./database/backup.sh

# 3. 새 패키지로 업데이트
# (새 패키지의 install.sh 실행)

# 4. 서비스 재시작
sudo systemctl start blacklist

# 5. 설치 검증
./scripts/health-check.sh
```

### 로그 관리

```bash
# 로그 순환 설정
sudo nano /etc/logrotate.d/blacklist

# 내용:
# /opt/blacklist/logs/*.log {
#     daily
#     missingok
#     rotate 30
#     compress
#     notifempty
#     create 644 root root
# }

# Docker 로그 제한
# docker-compose.yml에 추가:
# logging:
#   driver: "json-file"
#   options:
#     max-size: "10m"
#     max-file: "3"
```

## 🛡️ 보안 고려사항

### 네트워크 보안

```bash
# 방화벽 설정 (ufw 예시)
sudo ufw allow 32542/tcp  # 블랙리스트 웹 인터페이스
sudo ufw allow 22/tcp     # SSH (관리용)
sudo ufw enable

# iptables 예시
sudo iptables -A INPUT -p tcp --dport 32542 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -j DROP
```

### 접근 제어

```bash
# 사용자 권한 설정
sudo chown -R blacklist:blacklist /opt/blacklist
sudo chmod 750 /opt/blacklist
sudo chmod 600 /opt/blacklist/.env

# SSH 키 기반 인증 설정 (권장)
# /etc/ssh/sshd_config에서:
# PasswordAuthentication no
# PubkeyAuthentication yes
```

### 인증서 관리

```bash
# Let's Encrypt (인터넷 연결 시)
sudo certbot --nginx -d your-domain.com

# 내부 CA 인증서 (폐쇄망)
# 조직 내부 인증서 설치 및 설정
```

## ❗ 트러블슈팅

### 일반적인 문제 해결

#### 1. 서비스 시작 실패

```bash
# 서비스 상태 확인
sudo systemctl status blacklist

# 로그 확인
sudo journalctl -u blacklist --no-pager

# Docker 로그 확인
cd /opt/blacklist
docker-compose logs
```

#### 2. Docker 이미지 로드 실패

```bash
# Docker 서비스 상태 확인
sudo systemctl status docker

# 수동 이미지 로드
docker load -i docker-images/registry.jclee.me_blacklist_latest.tar

# 이미지 목록 확인
docker images
```

#### 3. 데이터베이스 연결 문제

```bash
# 데이터베이스 파일 권한 확인
ls -la /opt/blacklist/instance/

# 데이터베이스 재초기화
cd /opt/blacklist
python3 init_database.py --force
```

#### 4. 포트 충돌

```bash
# 포트 사용 상태 확인
sudo netstat -tulpn | grep :32542

# 프로세스 종료
sudo kill -9 <PID>

# 다른 포트로 변경
# .env 파일에서 PORT=다른포트 설정
```

#### 5. 메모리 부족

```bash
# 메모리 사용량 확인
free -h
top

# 스왑 추가 (임시 해결)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 로그 위치

- **설치 로그**: `/tmp/blacklist-install.log`
- **시스템 로그**: `journalctl -u blacklist`
- **애플리케이션 로그**: `/opt/blacklist/logs/`
- **Docker 로그**: `docker-compose logs`

### 지원 및 도움말

1. **문서 확인**: `/opt/blacklist/docs/`
2. **헬스체크**: `./scripts/health-check.sh`
3. **설정 검증**: `./tools/verify-installation.sh`
4. **성능 테스트**: `./tools/performance-test.py`

## 📈 성능 최적화

### 시스템 튜닝

```bash
# 파일 디스크립터 제한 증가
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 커널 파라미터 튜닝
echo "vm.max_map_count=262144" >> /etc/sysctl.conf
echo "net.core.somaxconn=65535" >> /etc/sysctl.conf
sysctl -p
```

### Docker 최적화

```bash
# Docker 로그 드라이버 설정
echo '{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}' | sudo tee /etc/docker/daemon.json

sudo systemctl restart docker
```

### 애플리케이션 튜닝

```bash
# .env 파일에 성능 관련 설정 추가
echo "WORKERS=4" >> /opt/blacklist/.env
echo "WORKER_CONNECTIONS=1000" >> /opt/blacklist/.env
echo "CACHE_SIZE=256MB" >> /opt/blacklist/.env
```

## 🔄 백업 및 복구

### 자동 백업 설정

```bash
# 백업 스크립트 복사 및 실행 권한 부여
sudo cp database/backup.sh /usr/local/bin/blacklist-backup
sudo chmod +x /usr/local/bin/blacklist-backup

# 백업 디렉토리 생성
sudo mkdir -p /backup/blacklist

# cron 작업 추가 (매일 오전 2시)
echo "0 2 * * * /usr/local/bin/blacklist-backup" | sudo crontab -
```

### 복구 절차

```bash
# 서비스 중지
sudo systemctl stop blacklist

# 백업에서 복구
cd /opt/blacklist
./database/restore.sh /backup/blacklist/latest.sql

# 서비스 재시작
sudo systemctl start blacklist
```

## 📞 지원 정보

### 기술 지원

- **문서**: 패키지 내 `docs/` 디렉토리
- **로그 분석**: 설치 및 운영 로그 확인
- **자가 진단**: 제공된 검증 도구 활용

### 버전 정보

- **패키지 버전**: 2.0.0
- **지원 기간**: 설치일로부터 1년
- **호환성**: Linux x86_64 플랫폼

---

이 가이드는 블랙리스트 시스템의 완전한 오프라인 배포를 위한 포괄적인 지침을 제공합니다. 각 단계를 신중히 따라하시고, 문제가 발생하면 트러블슈팅 섹션을 참조하세요.