# Blacklist Management System

블랙리스트 IP 관리 시스템 - FortiGate External Connector 통합

## 🚀 Quick Start

```bash
# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 초기화
python3 setup_database.py

# 개발 서버 실행
python3 app.py

# 또는 프로덕션 배포
./deploy.sh container
```

## 📋 주요 API Endpoints

### FortiGate 연동
- `GET /api/blacklist/active` - 활성 IP 목록 (플레인 텍스트)
- `GET /api/fortigate` - FortiGate External Connector JSON 형식
- `GET /health` - 헬스체크

### 관리 및 모니터링
- `GET /api/stats` - 시스템 통계
- `GET /api/search/{ip}` - IP 검색 및 히스토리
- `GET /api/stats/detection-trends` - 탐지 동향 분석

## 🏗️ 시스템 아키텍처

### 핵심 구조
```
blacklist/
├── app.py                  # 메인 진입점
├── core/
│   ├── app_compact.py      # 통합 Flask 애플리케이션
│   ├── blacklist.py        # 블랙리스트 관리 로직
│   └── database.py         # 데이터베이스 운영
├── config/                 # 환경별 설정
├── scripts/                # 백그라운드 서비스
├── utils/                  # 유틸리티 (캐시, 인증, 모니터링)
└── deploy.sh              # 통합 배포 스크립트
```

### 데이터 처리 흐름
1. **수집**: 외부 API에서 시간당 데이터 수집
2. **저장**: SQLite 데이터베이스 + 월별 파일 구조
3. **캐싱**: Redis를 통한 고성능 응답
4. **제공**: FortiGate External Connector 표준 준수
5. **만료**: 3개월 자동 데이터 보존 정책

## 🔧 배포 옵션

### Container 배포 (권장)
```bash
# 자동 감지 (Podman/Docker)
./deploy.sh container

# 특정 포트 지정
./deploy.sh container --port 8080
```

### 직접 배포
```bash
# Python 직접 실행
./deploy.sh python

# Gunicorn (프로덕션)
./deploy.sh gunicorn
```

### CI/CD 자동 배포
```bash
# main 브랜치 푸시 시 자동 배포
git push origin main
```

## 📊 운영 모니터링

### 서비스 상태 확인
```bash
# 헬스체크
curl http://localhost:2541/health

# 시스템 통계
curl http://localhost:2541/api/stats | python3 -m json.tool

# FortiGate 연동 테스트
curl http://localhost:2541/api/blacklist/active
```

### 백그라운드 서비스
```bash
# 데이터 업데이터 설정
./scripts/setup_updater_service.sh

# 수동 데이터 업데이트
python3 scripts/run_updater.py

# 로그 모니터링
tail -f logs/updater.log
```

## 🛡️ FortiGate 설정

### External Connector 설정
1. **Connector Type**: `HTTP`
2. **URL**: `http://your-server:2541/api/fortigate`
3. **Update Interval**: `5분`
4. **Format**: `JSON`

### 기존 텍스트 연동
- **URL**: `http://your-server:2541/api/blacklist/active`
- **Format**: `Text (one IP per line)`

## 📈 성능 및 확장성

### 기술 스택
- **Backend**: Flask + Gunicorn
- **Database**: SQLite (개발) / PostgreSQL (옵션)
- **Cache**: Redis
- **Container**: Docker/Podman 지원
- **CI/CD**: GitLab Runner

### 성능 최적화
- **압축**: 자동 gzip 응답 압축
- **캐싱**: Redis TTL 기반 캐싱
- **Rate Limiting**: 엔드포인트별 제한
- **Connection Pooling**: 데이터베이스 연결 풀링

## 📚 문서 및 가이드

- [시스템 아키텍처](docs/SYSTEM_ARCHITECTURE_REPORT.md)
- [운영 가이드](docs/OPERATIONS_GUIDE.md)
- [고급 기능](docs/ADVANCED_FEATURES.md)
- [배포 가이드](docs/DEPLOYMENT.md)
- [CI/CD 설정](docs/CICD_PIPELINE_GUIDE.md)
- [트러블슈팅](docs/TROUBLESHOOTING.md)

## 🔐 보안 및 인증

- SQL Injection 방지
- Input 검증 및 Sanitization
- Rate Limiting 및 DDoS 방지
- CORS 설정
- 환경별 보안 정책

## 📞 지원 및 기여

- **이슈 리포트**: GitLab Issues
- **기능 요청**: Merge Request
- **문서**: `docs/` 디렉토리
- **설정**: `CLAUDE.md` 참조

---

**현재 버전**: Compact v2.1  
**마지막 업데이트**: 2025.06.04  
**라이선스**: MIT# CI/CD Pipeline Trigger
