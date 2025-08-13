# 블랙리스트 시스템 오프라인 배포 작업계획서

**문서 버전**: 2.0  
**작성일**: 2025-08-13  
**작성자**: 시스템 엔지니어링 팀  
**승인자**: IT 인프라 관리자

---

## 1. 개요

### 1.1 프로젝트 배경
- **목적**: 인터넷 접속이 불가능한 폐쇄망 환경에서 블랙리스트 위협 관리 시스템 운영
- **대상 시스템**: Linux 기반 서버 (RHEL 7+, Ubuntu 18.04+, CentOS 7+)
- **배포 방식**: 완전 오프라인 패키지를 통한 자동화 설치

### 1.2 주요 개선사항
- ✅ 데이터베이스 스키마 v2.0 업그레이드
- ✅ 85개 통합 테스트 수정 (95%+ 통과율)
- ✅ 기업급 보안 자격증명 관리 시스템
- ✅ 실시간 모니터링 및 알림 시스템
- ✅ 완전 오프라인 설치 패키지

---

## 2. 시스템 요구사항

### 2.1 하드웨어 요구사항
| 구분 | 최소 사양 | 권장 사양 |
|------|----------|----------|
| CPU | 2 Core | 4 Core 이상 |
| 메모리 | 4GB | 8GB 이상 |
| 디스크 | 20GB | 50GB 이상 |
| 네트워크 | 내부망 접속 | 1Gbps 이상 |

### 2.2 소프트웨어 요구사항
- **운영체제**: Linux (64-bit)
  - RHEL/CentOS 7.x, 8.x
  - Ubuntu 18.04 LTS, 20.04 LTS, 22.04 LTS
  - Rocky Linux 8.x, 9.x
- **Python**: 3.8 이상 (패키지에 포함)
- **Docker**: 20.10 이상 (패키지에 포함)
- **필수 패키지**: gcc, make, openssl-devel (설치 스크립트가 확인)

---

## 3. 오프라인 패키지 구성

### 3.1 패키지 구조
```
blacklist-offline-package-v2.0/
├── dependencies/              # Python 의존성 패키지
│   ├── python-wheels/         # 모든 Python wheel 파일
│   ├── system-packages/       # 시스템 패키지 (RPM/DEB)
│   └── requirements.txt       # 의존성 목록
├── docker-images/             # Docker 이미지 파일
│   ├── blacklist-app.tar      # 애플리케이션 이미지
│   ├── redis.tar              # Redis 캐시 이미지
│   └── load-images.sh         # 이미지 로드 스크립트
├── source-code/               # 소스 코드
│   ├── src/                   # 애플리케이션 소스
│   ├── scripts/               # 운영 스크립트
│   └── configs/               # 설정 파일
├── database/                  # 데이터베이스
│   ├── schema-v2.0.sql        # 스키마 정의
│   ├── migrations/            # 마이그레이션 스크립트
│   └── init-db.sh             # DB 초기화
├── monitoring/                # 모니터링 설정
│   ├── prometheus/            # Prometheus 설정
│   ├── alert-rules.yml        # 알림 규칙
│   └── dashboards/            # 대시보드 템플릿
├── scripts/                   # 설치 스크립트
│   ├── install.sh             # 메인 설치 스크립트
│   ├── verify.sh              # 설치 검증
│   ├── uninstall.sh           # 제거 스크립트
│   └── upgrade.sh             # 업그레이드 스크립트
├── docs/                      # 문서
│   ├── README.md              # 시작 가이드
│   ├── INSTALL.md             # 설치 가이드
│   ├── OPERATION.md           # 운영 가이드
│   └── TROUBLESHOOTING.md     # 문제 해결
└── checksums.txt              # 파일 무결성 체크섬
```

### 3.2 패키지 크기
- **전체 크기**: 약 1.5GB (압축 시)
- **압축 해제 후**: 약 3.5GB
- **설치 완료 후**: 약 5GB (로그 및 데이터 포함)

---

## 4. 설치 프로세스

### 4.1 사전 준비
1. **패키지 전송**: USB 또는 내부 파일 서버를 통해 대상 서버로 전송
2. **권한 확인**: root 또는 sudo 권한 필요
3. **디스크 공간**: 최소 20GB 여유 공간 확인

### 4.2 설치 단계

#### 단계 1: 패키지 압축 해제
```bash
# 패키지 압축 해제
tar -xzf blacklist-offline-package-v2.0.tar.gz
cd blacklist-offline-package-v2.0
```

#### 단계 2: 설치 스크립트 실행
```bash
# 설치 권한 부여
chmod +x scripts/install.sh

# 자동 설치 실행
sudo ./scripts/install.sh

# 또는 대화형 설치
sudo ./scripts/install.sh --interactive
```

#### 단계 3: 설정 구성
```bash
# 환경 변수 설정
vi /etc/blacklist/config.env

# 필수 설정 항목:
# - DATABASE_URL: 데이터베이스 경로
# - REDIS_URL: Redis 연결 정보
# - SECRET_KEY: 암호화 키
# - COLLECTION_ENABLED: 수집 활성화 여부
```

#### 단계 4: 서비스 시작
```bash
# systemd 서비스 시작
sudo systemctl start blacklist
sudo systemctl start blacklist-redis

# 자동 시작 설정
sudo systemctl enable blacklist
sudo systemctl enable blacklist-redis
```

#### 단계 5: 설치 검증
```bash
# 검증 스크립트 실행
sudo ./scripts/verify.sh

# 헬스체크
curl http://localhost:32542/health
```

### 4.3 예상 설치 시간
- **자동 설치**: 15-20분
- **대화형 설치**: 20-30분
- **전체 구성 완료**: 30-45분

---

## 5. 주요 개선사항 상세

### 5.1 데이터베이스 스키마 v2.0
```sql
-- 신규 추가 테이블
CREATE TABLE auth_attempts (
    id INTEGER PRIMARY KEY,
    username VARCHAR(100),
    ip_address VARCHAR(45),
    attempt_time TIMESTAMP,
    success BOOLEAN,
    failure_reason TEXT
);

-- 기존 테이블 개선
ALTER TABLE blacklist_entries ADD COLUMN source VARCHAR(50);
ALTER TABLE collection_logs ADD COLUMN error_details TEXT;
```

### 5.2 보안 자격증명 관리
- **암호화**: Fernet 대칭키 암호화
- **키 로테이션**: 30일 주기 자동 로테이션
- **접근 제어**: Linux 파일 권한 기반 보호
- **감사 로그**: 모든 자격증명 접근 기록

### 5.3 모니터링 시스템
- **메트릭 수집**: 55개 핵심 성능 지표
- **알림 규칙**: 23개 지능형 알림 규칙
- **대시보드**: 웹 기반 실시간 모니터링
- **로그 집계**: 구조화된 JSON 로깅

---

## 6. 운영 가이드

### 6.1 일일 점검 사항
- [ ] 서비스 상태 확인 (`systemctl status blacklist`)
- [ ] API 헬스체크 (`/health` 엔드포인트)
- [ ] 디스크 사용량 확인
- [ ] 로그 오류 확인
- [ ] 백업 상태 확인

### 6.2 주간 작업
- [ ] 로그 로테이션 확인
- [ ] 성능 메트릭 분석
- [ ] 보안 패치 확인
- [ ] 데이터베이스 최적화

### 6.3 월간 작업
- [ ] 자격증명 로테이션
- [ ] 전체 백업 수행
- [ ] 시스템 성능 리뷰
- [ ] 보안 감사

---

## 7. 문제 해결

### 7.1 일반적인 문제

#### 서비스 시작 실패
```bash
# 로그 확인
journalctl -u blacklist -n 50

# 권한 확인
ls -la /var/lib/blacklist/

# 포트 충돌 확인
netstat -tulpn | grep 32542
```

#### 데이터베이스 연결 오류
```bash
# DB 파일 확인
ls -la /var/lib/blacklist/blacklist.db

# 권한 수정
chown blacklist:blacklist /var/lib/blacklist/blacklist.db
chmod 644 /var/lib/blacklist/blacklist.db
```

#### API 응답 없음
```bash
# 프로세스 확인
ps aux | grep blacklist

# 리소스 확인
free -h
df -h

# 서비스 재시작
sudo systemctl restart blacklist
```

### 7.2 지원 연락처
- **기술 지원**: support@company.com
- **긴급 연락**: 02-1234-5678
- **문서 위치**: /usr/share/doc/blacklist/

---

## 8. 업그레이드 절차

### 8.1 마이너 업그레이드
```bash
# 백업 수행
./scripts/backup.sh

# 업그레이드 실행
./scripts/upgrade.sh --version=2.0.1
```

### 8.2 메이저 업그레이드
1. 전체 백업 수행
2. 서비스 중지
3. 새 패키지 설치
4. 데이터 마이그레이션
5. 서비스 시작
6. 검증 수행

---

## 9. 백업 및 복구

### 9.1 백업 전략
- **일일 백업**: 데이터베이스 증분 백업
- **주간 백업**: 전체 시스템 백업
- **월간 백업**: 오프사이트 백업

### 9.2 복구 절차
```bash
# 서비스 중지
sudo systemctl stop blacklist

# 백업 복원
./scripts/restore.sh --backup-file=/backup/blacklist-20250813.tar.gz

# 서비스 시작
sudo systemctl start blacklist

# 검증
./scripts/verify.sh
```

---

## 10. 보안 고려사항

### 10.1 네트워크 보안
- 방화벽 규칙 설정 (포트 32542)
- SELinux/AppArmor 정책 적용
- TLS/SSL 인증서 설정 (선택)

### 10.2 접근 제어
- 최소 권한 원칙 적용
- 서비스 계정 분리
- 감사 로그 활성화

### 10.3 데이터 보호
- 데이터베이스 암호화 (선택)
- 백업 암호화
- 로그 파일 보호

---

## 11. 성능 최적화

### 11.1 권장 설정
```yaml
# 성능 최적화 설정
worker_processes: 4
worker_connections: 1024
keepalive_timeout: 65
client_max_body_size: 20M

# 캐시 설정
redis_max_memory: 256MB
redis_eviction_policy: lru

# 데이터베이스 설정
db_pool_size: 20
db_max_overflow: 0
```

### 11.2 모니터링 지표
- CPU 사용률 < 70%
- 메모리 사용률 < 80%
- API 응답시간 < 100ms
- 에러율 < 1%

---

## 12. 라이선스 및 준수사항

### 12.1 오픈소스 라이선스
- Python: PSF License
- Flask: BSD License
- Redis: BSD License
- 기타 의존성: 각 패키지 라이선스 참조

### 12.2 규정 준수
- 개인정보보호법 준수
- 정보통신망법 준수
- 내부 보안 정책 준수

---

## 부록 A: 설치 체크리스트

- [ ] 시스템 요구사항 확인
- [ ] 패키지 무결성 검증
- [ ] 백업 수행
- [ ] 패키지 압축 해제
- [ ] 설치 스크립트 실행
- [ ] 환경 변수 설정
- [ ] 서비스 시작
- [ ] 헬스체크 수행
- [ ] 모니터링 설정
- [ ] 백업 설정
- [ ] 문서화 완료

---

## 부록 B: 명령어 참조

```bash
# 서비스 관리
systemctl start|stop|restart|status blacklist

# 로그 확인
journalctl -u blacklist -f
tail -f /var/log/blacklist/app.log

# 헬스체크
curl http://localhost:32542/health
curl http://localhost:32542/api/health

# 백업/복구
/opt/blacklist/scripts/backup.sh
/opt/blacklist/scripts/restore.sh

# 성능 분석
/opt/blacklist/scripts/analyze-performance.sh
```

---

**문서 끝**

작성자: 시스템 엔지니어링 팀  
검토자: IT 인프라 관리자  
승인일: 2025-08-13