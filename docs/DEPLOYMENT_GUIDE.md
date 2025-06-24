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
**시스템 버전**: v2.1-compact-unified