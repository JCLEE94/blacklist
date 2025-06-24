# Scripts 디렉토리

스크립트들이 기능별로 정리되어 있습니다.

## 디렉토리 구조

### `/collection/` - 데이터 수집 스크립트
- **REGTECH**: 금융보안원 데이터 수집 관련 스크립트
- **SECUDIUM**: SECUDIUM 위협 인텔리전스 수집 관련 스크립트  
- **공통**: 데이터 검증, 파싱, 통합 스크립트

### `/deployment/` - 배포 및 서비스 관리
- 자동 배포 스크립트
- 서비스 설정 및 관리
- 업데이터 서비스 관련

### `/maintenance/` - 유지보수 및 백업
- 데이터베이스 백업
- 시스템 정리 및 최적화
- 로그 관리

### `/archive/` - 아카이브된 스크립트
- 더 이상 사용하지 않는 스크립트
- 레거시 코드 보관

## 주요 스크립트 사용법

### 데이터 수집
```bash
# REGTECH 데이터 수집
python3 scripts/collection/regtech_auto_collector.py

# SECUDIUM 데이터 수집  
python3 scripts/collection/secudium_auto_collector.py
```

### 배포
```bash
# 서비스 배포
./scripts/deployment/setup_updater_service.sh

# 자동 업데이터 실행
python3 scripts/deployment/run_updater.py
```

### 유지보수
```bash
# 데이터베이스 백업
python3 scripts/maintenance/backup_manager.py

# 시스템 정리
python3 scripts/maintenance/cleanup_old_data.py
```