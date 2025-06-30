# Scripts Directory - 용도별 폴더 구조

이 디렉토리는 Blacklist Management System의 각종 스크립트와 도구들을 용도별로 정리한 구조입니다.

## 📁 폴더 구조 및 용도

### 🚀 `/deployment/` - 배포 관련 스크립트
**용도**: 프로덕션 배포, 환경 설정, 볼륨 관리
```
deployment/
├── deploy-env.sh              # 환경 변수 설정 및 배포
├── deploy-single.sh           # 단일 컨테이너 배포
├── manage-volumes.sh          # Docker 볼륨 관리
├── production-setup.sh        # 프로덕션 환경 초기 설정
└── run_updater.py            # 자동 업데이트 스크립트
```

### 📊 `/collection/` - 데이터 수집 스크립트
**용도**: REGTECH, SECUDIUM 데이터 수집 및 처리
```
collection/
├── README.md                  # 수집 스크립트 가이드
├── collect_regtech_simple.py  # 간단한 REGTECH 수집기
├── generate_sample_regtech.py # 테스트용 REGTECH 데이터 생성
├── import_secudium_excel.py   # SECUDIUM Excel 파일 처리
├── regtech_date_range_collector.py  # 날짜 범위별 REGTECH 수집
├── regtech_har_collector.py   # HAR 기반 REGTECH 수집기
├── secudium_api_collector.py  # SECUDIUM API 수집기
├── secudium_auto_collector.py # SECUDIUM 자동 수집기
├── setup_regtech_cron.sh     # REGTECH 크론잡 설정
├── simple_regtech_collector.py # 기본 REGTECH 수집기
└── simple_secudium_collector.py # 기본 SECUDIUM 수집기
```

### 📈 `/analysis/` - 데이터 분석 도구
**용도**: 수집된 데이터 분석, 통계 생성, 리포트 작성
```
analysis/
└── (분석 관련 스크립트들)
```

### 🛠️ `/setup/` - 초기 설정 스크립트
**용도**: 데이터베이스 초기화, 시스템 설정
```
setup/
├── check_db_structure.py     # 데이터베이스 구조 검증
└── database_cleanup_and_setup.py # DB 정리 및 초기 설정
```

### 🔧 `/manual/` - 수동 작업 스크립트
**용도**: 일회성 작업, 데이터 마이그레이션, 긴급 수정
```
manual/
├── add_expiration_support.py # 만료 지원 기능 추가
├── check_detection_dates.py  # 탐지 날짜 확인
├── create_ip_detection_table.py # IP 탐지 테이블 생성
├── create_test_expiration_data.py # 테스트 만료 데이터 생성
├── fix_db_schema.py          # 데이터베이스 스키마 수정
├── fix_db_simple.py          # 간단한 DB 수정
├── fix_production_db.py      # 프로덕션 DB 수정
├── fix_regtech_auth.py       # REGTECH 인증 문제 수정
├── init_db.py               # 데이터베이스 초기화
├── main.py                  # 수동 작업용 메인 스크립트
└── migrate_db.py            # 데이터베이스 마이그레이션
```

## 📄 루트 레벨 스크립트

### 🐳 Docker 관련
- `check-docker-volumes.sh` - Docker 볼륨 상태 확인
- `check-watchtower-logs.sh` - Watchtower 로그 확인
- `create-volume-structure.sh` - 볼륨 구조 생성
- `fix-docker-volumes.sh` - Docker 볼륨 문제 해결
- `fix-watchtower.sh` - Watchtower 문제 해결
- `setup-watchtower.sh` - Watchtower 초기 설정

### 🚀 배포 관련
- `deploy-single-to-production.sh` - 단일 컨테이너 프로덕션 배포
- `force-update-production.sh` - 강제 프로덕션 업데이트
- `switch-to-single-container.sh` - 단일 컨테이너 모드 전환

### 🔧 시스템 관리
- `check_db_schema.py` - 데이터베이스 스키마 확인
- `fix_database.py` - 데이터베이스 문제 해결
- `fix_database_schema.py` - 스키마 문제 수정
- `final_test.py` - 최종 테스트 스크립트

### 🐙 GitHub 관련
- `github-setup.sh` - GitHub Actions 설정
- `set-github-secrets.sh` - GitHub Secrets 설정

### 🧪 테스트
- `integration_test_comprehensive.py` - 종합 통합 테스트

### ☸️ Kubernetes 관리
- `k8s-management.ps1` - **NEW!** Windows PowerShell용 Kubernetes 관리 도구

## 🎯 주요 사용 사례

### 1. 새로운 환경 설정
```bash
# 1. 초기 설정
./setup/database_cleanup_and_setup.py
./github-setup.sh
./setup-watchtower.sh

# 2. 데이터 수집 설정
./collection/setup_regtech_cron.sh
```

### 2. 데이터 수집 문제 해결
```bash
# REGTECH 문제
./manual/fix_regtech_auth.py
./collection/regtech_har_collector.py

# SECUDIUM 문제
./collection/secudium_auto_collector.py
```

### 3. 프로덕션 배포
```bash
# 단일 컨테이너 배포
./deployment/deploy-single.sh

# 볼륨 관리
./deployment/manage-volumes.sh

# 강제 업데이트
./force-update-production.sh
```

### 4. Windows에서 Kubernetes 관리
```powershell
# PowerShell에서 실행
.\k8s-management.ps1 deploy    # 배포
.\k8s-management.ps1 status    # 상태 확인
.\k8s-management.ps1 scale 4   # 스케일링
.\k8s-management.ps1 logs      # 로그 확인
```

### 5. 문제 진단 및 해결
```bash
# Docker 관련
./check-docker-volumes.sh
./fix-docker-volumes.sh

# 데이터베이스 관련
./check_db_schema.py
./fix_database_schema.py

# 통합 테스트
./integration_test_comprehensive.py
```

## 🔐 보안 주의사항

- **인증 정보**: collection/ 폴더의 스크립트들은 실제 인증 정보가 필요합니다
- **프로덕션 접근**: deployment/ 폴더의 스크립트들은 프로덕션 환경에 직접 영향을 줍니다
- **데이터 변경**: manual/ 폴더의 스크립트들은 데이터를 직접 수정할 수 있습니다

## 📝 기여 가이드라인

새로운 스크립트를 추가할 때는 다음 규칙을 따라주세요:

1. **명확한 파일명**: 용도를 명확히 나타내는 이름 사용
2. **적절한 폴더**: 용도에 맞는 폴더에 배치
3. **문서화**: 스크립트 상단에 용도와 사용법 주석 추가
4. **에러 처리**: 적절한 에러 처리 로직 포함
5. **로깅**: 작업 진행 상황을 명확히 출력

---

**주의**: 프로덕션 환경에서 스크립트를 실행하기 전에 반드시 테스트 환경에서 검증하세요.