# Blacklist Management System - 운영 가이드

## 시스템 개요

**Blacklist Management System**은 REGTECH 및 SECUDIUM으로부터 수집된 위협 정보를 통합 관리하는 고가용성 보안 플랫폼입니다.

### 핵심 기능
- 🔍 **멀티소스 데이터 수집**: REGTECH, SECUDIUM 자동/수동 수집
- 🛡️ **실시간 위협 탐지**: 49,217개 활성 IP 모니터링
- 🚀 **고성능 API**: FortiGate 연동 및 RESTful API
- 📊 **통합 대시보드**: 실시간 통계 및 분석
- 🔄 **자동화된 CI/CD**: GitLab 기반 배포 자동화
- 💾 **안정적인 백업**: 자동 백업 및 복구 시스템

## 1. 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Application   │    │    Database     │
│     (Nginx)     │◄───┤   (Flask)       │◄───┤   (SQLite)      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Monitoring    │    │      Cache      │    │     Backup      │
│   (Custom)      │    │    (Redis)      │    │    (Auto)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 포트 구성
- **개발환경**: 1541
- **프로덕션**: 2541
- **로드밸런서**: 80, 443
- **모니터링**: 8080

## 2. 배포 환경

### 원격 서버 (Synology NAS)
- **주소**: 192.168.50.215:1111
- **사용자**: docker
- **경로**: ~/app/blacklist
- **Docker**: Container Manager

### 로컬 개발환경
- **포트**: 2541
- **데이터베이스**: instance/blacklist.db
- **캐시**: Redis (옵션)

## 3. 배포 방법

### 방법 1: 자동 배포 (권장)
```bash
# GitLab CI/CD를 통한 자동 배포
git add .
git commit -m "Deploy to production"
git push origin main
```

### 방법 2: 수동 배포
```bash
# 로컬에서 원격 서버로 배포
./deploy_to_remote.sh

# 또는 스크립트를 통한 배포
ssh -p 1111 docker@192.168.50.215 "cd ~/app/blacklist && ./start.sh"
```

### 방법 3: 스케일링 배포
```bash
# 멀티 인스턴스 배포
docker-compose -f docker-compose.scaling.yml up -d

# 스케일 업/다운
./scripts/scale_up.sh
./scripts/scale_down.sh
```

## 4. 운영 명령어

### 기본 운영
```bash
# 시스템 시작
./start.sh

# 시스템 중지
./stop.sh

# 시스템 재시작
./update.sh

# 상태 확인
./monitor.sh
```

### 백업 관리
```bash
# 수동 백업
python3 scripts/database_backup_system.py backup --type manual --compress

# 백업 목록 확인
python3 scripts/database_backup_system.py list

# 백업 복구
python3 scripts/database_backup_system.py restore --file <backup_file>

# 백업 스케줄러 시작
python3 scripts/backup_scheduler.py daemon
```

### 모니터링
```bash
# 실시간 모니터링
python3 scripts/monitoring_system.py daemon

# 단발성 상태 확인
python3 scripts/monitoring_system.py check

# 성능 최적화
python3 scripts/performance_optimizer.py full
```

### 보안 관리
```bash
# 보안 감사
python3 scripts/security_audit.py audit

# 보안 키 생성
python3 scripts/security_audit.py keys

# 권한 검사
python3 scripts/security_audit.py permissions
```

## 5. 데이터 수집

### REGTECH 수집
```bash
# 자동 수집
python3 scripts/regtech_auto_collector.py

# 완전 수집
python3 scripts/regtech_complete_collector.py

# ZIP 분석
python3 scripts/regtech_zip_analyzer.py
```

### SECUDIUM 수집
```bash
# API 기반 수집
python3 scripts/secudium_api_collector.py

# Excel 가져오기
python3 scripts/import_secudium_excel.py
```

## 6. API 엔드포인트

### 핵심 API
```bash
# 헬스체크
curl http://localhost:2541/health

# 활성 IP 목록 (FortiGate 형식)
curl http://localhost:2541/api/fortigate

# 시스템 통계
curl http://localhost:2541/api/stats

# IP 검색
curl -X POST http://localhost:2541/api/search \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.1"}'

# 컬렉션 상태
curl http://localhost:2541/api/collection/status
```

### 고급 API
```bash
# 향상된 블랙리스트
curl http://localhost:2541/api/v2/blacklist/enhanced

# 분석 트렌드
curl http://localhost:2541/api/v2/analytics/trends

# 성능 메트릭
curl http://localhost:2541/api/v2/monitoring/performance
```

## 7. 웹 인터페이스

### 주요 페이지
- **대시보드**: http://localhost:2541/
- **데이터 관리**: http://localhost:2541/data-management
- **IP 검색**: http://localhost:2541/blacklist-search
- **연결 상태**: http://localhost:2541/connection-status
- **시스템 로그**: http://localhost:2541/system-logs

## 8. 로그 관리

### 로그 위치
```
logs/
├── app.log                    # 애플리케이션 로그
├── monitoring.log             # 모니터링 로그
├── backup_system.log          # 백업 시스템 로그
├── security_audit.log         # 보안 감사 로그
├── performance_report_*.json  # 성능 리포트
└── nginx/                     # Nginx 로그
    ├── access.log
    └── error.log
```

### 로그 정리
```bash
# 자동 로그 정리
./cleanup-logs.sh

# 수동 로그 압축
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
```

## 9. 문제 해결

### 일반적인 문제

#### 1. 서비스가 시작되지 않는 경우
```bash
# 포트 사용 확인
netstat -tlnp | grep 2541

# 프로세스 종료
pkill -f "python.*main.py"

# 로그 확인
tail -f logs/app.log
```

#### 2. 데이터베이스 오류
```bash
# 데이터베이스 무결성 검사
sqlite3 instance/blacklist.db "PRAGMA integrity_check;"

# 백업에서 복구
python3 scripts/database_backup_system.py restore --file <최신_백업>
```

#### 3. 메모리 부족
```bash
# 메모리 사용량 확인
free -h

# 캐시 정리
echo 3 > /proc/sys/vm/drop_caches

# 성능 최적화
python3 scripts/performance_optimizer.py full
```

#### 4. Docker 컨테이너 문제
```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f app

# 컨테이너 재시작
docker-compose restart app
```

### 비상 복구 절차

#### 완전 시스템 복구
```bash
# 1. 기존 시스템 백업
tar -czf emergency_backup_$(date +%Y%m%d_%H%M%S).tar.gz .

# 2. 최신 코드 가져오기
git pull origin main

# 3. 의존성 재설치
pip install -r requirements.txt

# 4. 데이터베이스 복구
python3 scripts/database_backup_system.py restore --file <최신_백업>

# 5. 시스템 재시작
./start.sh
```

## 10. 성능 최적화

### 권장 설정
```bash
# 데이터베이스 최적화
python3 scripts/performance_optimizer.py optimize-db

# 시스템 리소스 모니터링
watch -n 5 './monitor.sh'

# 로드 밸런싱 활성화
docker-compose -f docker-compose.scaling.yml up -d
```

### 성능 지표
- **응답 시간**: < 100ms (캐시 적중)
- **메모리 사용**: < 2GB per instance
- **CPU 사용**: < 50% under load
- **데이터베이스**: 49,217 IPs, 59MB

## 11. 보안 가이드

### 보안 체크리스트
- [x] 입력 검증 및 SQL 인젝션 방지
- [x] API 인증 및 권한 관리
- [x] 요청 속도 제한
- [x] 로깅 및 모니터링
- [x] 정기 백업
- [ ] HTTPS 강제 적용
- [ ] 방화벽 규칙 설정
- [ ] 침입 탐지 시스템

### 보안 키 관리
```bash
# 새 보안 키 생성
python3 scripts/security_audit.py keys

# 환경 변수 설정
source .env.security

# 권한 설정
chmod 600 .env.security
```

## 12. 유지보수

### 정기 작업 (자동화됨)
- **일일**: 데이터베이스 백업 (02:00 KST)
- **주간**: 전체 시스템 백업 (일요일 03:00 KST)
- **월간**: 아카이브 백업 (1일 04:00 KST)
- **매시간**: 상태 모니터링 및 알림

### 수동 작업 (권장)
- **월간**: 보안 감사 실행
- **분기**: 의존성 업데이트
- **반기**: 재해 복구 테스트
- **연간**: 전체 시스템 검토

## 13. 연락처 및 지원

### 기술 지원
- **관리자**: admin@jclee.me
- **시스템 로그**: logs/
- **모니터링 대시보드**: http://localhost:2541/
- **상태 페이지**: http://localhost:2541/health

### 문서
- **API 문서**: CLAUDE.md
- **개발 가이드**: README.md
- **변경 이력**: Git commit history

---

## 빠른 참조

### 즉시 사용 명령어
```bash
# 시스템 상태 확인
curl -s http://localhost:2541/health | jq '.'

# 현재 IP 수
curl -s http://localhost:2541/api/stats | jq '.summary.total_ips'

# 최신 백업 생성
python3 scripts/database_backup_system.py backup --type manual

# 전체 시스템 최적화
python3 scripts/performance_optimizer.py full

# 보안 감사
python3 scripts/security_audit.py audit
```

### 환경별 URL
- **로컬 개발**: http://localhost:2541
- **원격 프로덕션**: http://192.168.50.215:2541
- **로드 밸런서**: http://192.168.50.215

---

**마지막 업데이트**: 2025-06-18 14:22:00 KST  
**문서 버전**: 1.0.0  
**시스템 버전**: v2.1-compact-unified# 🚀 Blacklist Management System - 배포 상태

## ✅ CI/CD 설정 완료

### GitHub 저장소
- **URL**: https://github.com/qws941/blacklist-management
- **Branch**: main
- **Status**: ✅ 코드 푸시 완료

### GitHub Actions
- **Workflows**: 3개 구성 완료
  - `build-deploy.yml` - 빌드 및 배포
  - `pr-checks.yml` - PR 검사  
  - `scheduled-collection.yml` - 스케줄 수집
- **Status**: 🔄 빌드 진행 중
  - **Run ID**: 15844125149 (레지스트리 인증 수정 후 재실행)
  - **Current Step**: Docker 이미지 빌드 및 푸시
  - **Progress**: 
    - ✅ 저장소 체크아웃
    - ✅ Docker Buildx 설정
    - ✅ 프라이빗 레지스트리 로그인 성공
    - ✅ 메타데이터 추출
    - 🔄 Docker 이미지 빌드 및 푸시 (진행 중)

### GitHub Secrets (✅ 모두 설정됨)
```
REGISTRY_USERNAME=qws941
REGISTRY_PASSWORD=********
DEPLOY_HOST=registry.jclee.me
DEPLOY_PORT=1112
DEPLOY_USER=docker
DEPLOY_SSH_KEY=********
```

### Docker Registry
- **Registry**: registry.jclee.me
- **Image**: registry.jclee.me/blacklist-management:latest
- **Authentication**: Public access (no auth required)

### 배포 대상 서버
- **Host**: registry.jclee.me:1112
- **User**: docker
- **Path**: /home/docker/blacklist

## 📋 배포 프로세스

1. **코드 푸시** → GitHub Actions 트리거
2. **빌드** → Docker 이미지 생성 (amd64/arm64)
3. **테스트** → pytest 실행
4. **보안 스캔** → Trivy 취약점 검사
5. **푸시** → registry.jclee.me로 이미지 푸시
6. **배포** → SSH로 서버 접속 후 컨테이너 업데이트
7. **헬스 체크** → /health 엔드포인트 확인

## 🔍 현재 상태 확인 방법

### GitHub Actions 상태
```bash
# CLI로 확인
gh run list --repo qws941/blacklist-management

# 웹에서 확인
https://github.com/qws941/blacklist-management/actions
```

### 배포된 서비스 확인
```bash
# 헬스 체크
curl http://registry.jclee.me:2541/health

# API 상태
curl http://registry.jclee.me:2541/api/stats
```

## ⚠️ 알려진 이슈

1. **Dependabot PR 과다 생성**
   - 임시로 비활성화함 (dependabot-disabled.yml)
   - 필요시 파일명을 dependabot.yml로 변경하여 재활성화

2. **초기 빌드 시간**
   - 첫 빌드는 모든 의존성 설치로 인해 시간이 걸림
   - 이후 빌드는 캐시 사용으로 빨라짐

## 📊 예상 소요 시간

- **빌드**: 5-10분
- **테스트**: 2-3분
- **배포**: 2-3분
- **총 시간**: 약 10-15분

## 🎯 다음 단계

1. GitHub Actions 실행 완료 대기
2. 배포 서버에서 서비스 상태 확인
3. 필요시 로그 확인 및 디버깅

## 🔧 수정 사항

### 프라이빗 레지스트리 인증 추가 (2025-06-24 16:28)
- 문제: 프라이빗 레지스트리 푸시 시 인증 누락
- 해결: `docker/login-action@v3` 추가하여 레지스트리 인증 설정
- 결과: 레지스트리 로그인 성공, 이미지 푸시 진행 중

### 워크플로우 간소화 (2025-06-24 16:32)
- 변경: 배포 단계 제거, 빌드와 푸시만 수행
- 이유: 레지스트리 푸시까지만 성공 확인 요청
- 결과: 워크플로우가 `Build and Push`로 단순화됨

---

마지막 업데이트: 2025-06-24 16:32 KST# 🚀 운영 환경 배포 가이드

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
3. 시스템 상태: `docker-compose ps`# 🐳 Watchtower 자동 배포 가이드

## 개요

Watchtower를 사용하여 Docker 이미지가 업데이트되면 자동으로 컨테이너를 재시작하는 CI/CD 파이프라인입니다.

## 구성 요소

### 1. docker-compose.watchtower.yml
- **blacklist-app**: 메인 애플리케이션 컨테이너
- **blacklist-redis**: Redis 캐시 서버
- **watchtower**: 자동 업데이트 모니터

### 2. 레지스트리 정보
- **Registry**: registry.jclee.me
- **Image**: registry.jclee.me/blacklist-management:latest
- **Port**: 2541 (호스트) → 8541 (컨테이너)

## 초기 설정

### 1. 자동 설정 (권장)
```bash
./scripts/setup-watchtower.sh
```

### 2. 수동 설정
```bash
# 1. 레지스트리 인증 파일 생성
echo -n "qws941:bingogo1l7!" | base64 > auth.txt
cat > watchtower-config.json << EOF
{
  "auths": {
    "registry.jclee.me": {
      "auth": "$(cat auth.txt)"
    }
  }
}
EOF
rm auth.txt

# 2. 권한 설정
chmod 600 watchtower-config.json

# 3. 컨테이너 시작
docker-compose -f docker-compose.watchtower.yml up -d
```

## 운영 명령어

### 서비스 관리
```bash
# 시작
docker-compose -f docker-compose.watchtower.yml up -d

# 중지
docker-compose -f docker-compose.watchtower.yml down

# 재시작
docker-compose -f docker-compose.watchtower.yml restart

# 상태 확인
docker-compose -f docker-compose.watchtower.yml ps
```

### 로그 확인
```bash
# 전체 로그
docker-compose -f docker-compose.watchtower.yml logs -f

# 애플리케이션 로그
docker logs blacklist-app -f

# Watchtower 로그 (업데이트 확인)
docker logs watchtower -f

# Redis 로그
docker logs blacklist-redis -f
```

### 수동 업데이트
```bash
# 즉시 업데이트 확인
docker exec watchtower /watchtower --run-once

# 특정 컨테이너만 업데이트
docker exec watchtower /watchtower --run-once blacklist-app
```

## 모니터링

### 헬스 체크
```bash
# 애플리케이션 상태
curl http://localhost:2541/health

# API 통계
curl http://localhost:2541/api/stats

# 컨테이너 상태
docker ps | grep blacklist
```

### Watchtower 동작 확인
```bash
# 마지막 업데이트 시간 확인
docker logs watchtower | grep "Checking for available updates"

# 업데이트 이벤트 확인
docker logs watchtower | grep "Found new"
```

## 문제 해결

### 1. 이미지 Pull 실패
```bash
# 레지스트리 연결 테스트
docker pull registry.jclee.me/blacklist-management:latest

# 인증 확인
cat watchtower-config.json | jq .

# 수동 로그인 테스트
docker login registry.jclee.me -u qws941 -p bingogo1l7!
```

### 2. 컨테이너 재시작 실패
```bash
# 기존 컨테이너 제거
docker-compose -f docker-compose.watchtower.yml down
docker system prune -f

# 깨끗한 시작
docker-compose -f docker-compose.watchtower.yml up -d --force-recreate
```

### 3. 네트워크 문제
```bash
# 네트워크 재생성
docker network rm blacklist_blacklist-net
docker-compose -f docker-compose.watchtower.yml up -d
```

## 보안 주의사항

1. **watchtower-config.json**은 절대 Git에 커밋하지 마세요
2. 파일 권한은 반드시 600으로 설정하세요
3. 프로덕션 환경에서는 더 안전한 비밀 관리 방법을 사용하세요

## 업데이트 주기

- **기본값**: 5분 (300초)
- **변경 방법**: `WATCHTOWER_POLL_INTERVAL` 환경 변수 수정
- **권장 설정**: 
  - 개발: 60초
  - 스테이징: 300초 (5분)
  - 프로덕션: 600초 (10분)

## CI/CD 플로우

1. 코드 푸시 → GitHub Actions 트리거
2. Docker 이미지 빌드 → registry.jclee.me 푸시
3. Watchtower가 새 이미지 감지 (5분 이내)
4. 자동으로 컨테이너 재시작
5. 헬스 체크로 정상 동작 확인

## 모니터링 대시보드

향후 Prometheus + Grafana 연동 예정:
- 컨테이너 메트릭
- 업데이트 이벤트
- 애플리케이션 성능
- Redis 캐시 히트율