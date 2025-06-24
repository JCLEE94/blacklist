# 🚀 운영 환경 배포 가이드

## 빠른 시작 (Quick Start)

### 1. 원클릭 설치
```bash
# 스크립트 다운로드 및 실행
curl -sSL https://raw.githubusercontent.com/qws941/blacklist-management/main/deployment/production-setup.sh | sudo bash
```

### 2. 수동 설치
```bash
# 1. 작업 디렉토리 생성
sudo mkdir -p /opt/blacklist
cd /opt/blacklist

# 2. docker-compose.yml 다운로드
sudo curl -o docker-compose.yml https://raw.githubusercontent.com/qws941/blacklist-management/main/deployment/docker-compose.watchtower.yml

# 3. 설정 디렉토리 생성
sudo mkdir -p config instance logs data

# 4. 레지스트리 인증 설정
echo -n "qws941:bingogo1l7!" | base64 > auth.txt
sudo tee config/watchtower-config.json << EOF
{
  "auths": {
    "registry.jclee.me": {
      "auth": "$(cat auth.txt)"
    }
  }
}
EOF
rm auth.txt
sudo chmod 600 config/watchtower-config.json

# 5. 서비스 시작
sudo docker-compose up -d
```

## 시스템 요구사항

- Docker 20.10+ 및 Docker Compose 1.29+
- 최소 2GB RAM
- 10GB 여유 디스크 공간
- 포트 2541 사용 가능

## 설치 후 확인

### 헬스 체크
```bash
curl http://localhost:2541/health
```

### 서비스 상태
```bash
docker-compose ps
```

### 로그 확인
```bash
# 전체 로그
docker-compose logs -f

# 애플리케이션 로그만
docker logs blacklist-app -f

# Watchtower 로그 (업데이트 확인)
docker logs watchtower -f
```

## 자동 업데이트

Watchtower가 5분마다 새 이미지를 확인하고 자동으로 업데이트합니다.

### 업데이트 확인
```bash
docker logs watchtower | grep "Found new"
```

### 수동 업데이트 트리거
```bash
docker exec watchtower /watchtower --run-once
```

## 운영 관리

### 서비스 관리
```bash
# 시작
docker-compose up -d

# 중지
docker-compose down

# 재시작
docker-compose restart

# 특정 서비스만 재시작
docker-compose restart blacklist-app
```

### 백업
```bash
# 데이터 백업
tar -czf backup-$(date +%Y%m%d).tar.gz instance/ data/

# Redis 백업
docker exec blacklist-redis redis-cli BGSAVE
```

### 모니터링
```bash
# 리소스 사용량
docker stats

# 디스크 사용량
du -sh /opt/blacklist/*
```

## 문제 해결

### 포트 충돌
```bash
# 2541 포트 사용 중인 프로세스 확인
sudo lsof -i :2541

# docker-compose.yml에서 포트 변경
# ports:
#   - "3541:8541"  # 외부포트:내부포트
```

### 이미지 Pull 실패
```bash
# 수동 로그인
docker login registry.jclee.me -u qws941 -p bingogo1l7!

# 이미지 직접 pull
docker pull registry.jclee.me/blacklist-management:latest
```

### 메모리 부족
```bash
# Redis 메모리 제한 조정 (docker-compose.yml)
command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

## 보안 설정

### 방화벽 설정 (UFW)
```bash
# 특정 IP에서만 접근 허용
sudo ufw allow from 192.168.0.0/16 to any port 2541

# 모든 IP에서 접근 허용 (권장하지 않음)
sudo ufw allow 2541
```

### HTTPS 설정 (Nginx 리버스 프록시)
```nginx
server {
    listen 443 ssl http2;
    server_name blacklist.example.com;

    ssl_certificate /etc/ssl/certs/blacklist.crt;
    ssl_certificate_key /etc/ssl/private/blacklist.key;

    location / {
        proxy_pass http://localhost:2541;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 업그레이드 절차

### 무중단 업그레이드
1. 새 이미지가 registry.jclee.me에 푸시됨
2. Watchtower가 5분 이내 자동 감지
3. 롤링 재시작으로 무중단 업그레이드

### 수동 업그레이드
```bash
# 최신 이미지 pull
docker pull registry.jclee.me/blacklist-management:latest

# 재시작
docker-compose up -d
```

## 롤백 절차

```bash
# 이전 버전으로 롤백
docker-compose down
docker run -d --name blacklist-app \
  -p 2541:8541 \
  registry.jclee.me/blacklist-management:previous-tag

# 또는 특정 커밋 해시로
docker pull registry.jclee.me/blacklist-management:main-abc123
docker-compose up -d
```

## 성능 튜닝

### Docker 리소스 제한
```yaml
# docker-compose.yml에 추가
services:
  blacklist-app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Redis 최적화
```yaml
# Redis 설정 최적화
command: >
  redis-server
  --maxmemory 1gb
  --maxmemory-policy allkeys-lru
  --save 900 1
  --save 300 10
  --save 60 10000
```

## 로그 관리

### 로그 로테이션
```bash
# /etc/logrotate.d/blacklist 생성
/opt/blacklist/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
```

## 모니터링 통합

### Prometheus 메트릭
- http://localhost:2541/metrics (향후 추가 예정)

### 알림 설정
Watchtower 알림을 Slack으로 전송:
```yaml
environment:
  - WATCHTOWER_NOTIFICATIONS=slack
  - WATCHTOWER_NOTIFICATION_SLACK_HOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

## 지원

문제 발생 시:
1. 로그 확인: `docker-compose logs`
2. GitHub Issues: https://github.com/qws941/blacklist-management/issues
3. 시스템 상태: `docker-compose ps`