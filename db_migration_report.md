# 📊 데이터베이스 마이그레이션 보고서

## 실행 시간: 2025-08-28 12:37:53

## 📈 분석 결과

### 데이터베이스 현황

#### BLACKLIST
- 파일 수: 3개
- 총 크기: 1968.0KB
  - instance/blacklist.db: 748.0KB
    • metadata: 1 rows
    • blacklist_entries: 0 rows
    • sqlite_sequence: 6 rows
    • collection_logs: 0 rows
    • auth_attempts: 0 rows
    • system_status: 0 rows
    • cache_entries: 0 rows
    • system_logs: 0 rows
    • collection_sources: 0 rows
    • collection_credentials: 0 rows
    • collection_settings: 3 rows
    • collection_history: 0 rows
    • blacklist: 2795 rows
    • protection_events: 28 rows
    • collection_config: 2 rows
    • collection_status: 1 rows
    • app_settings: 14 rows
  - instance/blacklist_dev.db: 192.0KB
    • metadata: 1 rows
    • blacklist_entries: 3 rows
    • sqlite_sequence: 1 rows
    • collection_logs: 0 rows
    • auth_attempts: 0 rows
    • system_status: 0 rows
    • cache_entries: 0 rows
    • system_logs: 0 rows
    • blacklist_ip: 0 rows
  - data/blacklist.db: 340.0KB
    • collection_logs: 309 rows
    • sqlite_sequence: 3 rows
    • collection_sources: 0 rows
    • collection_credentials: 0 rows
    • collection_settings: 0 rows
    • collection_history: 0 rows
    • collection_config: 6 rows
    • collection_status: 1 rows
    • metadata: 1 rows
    • blacklist_entries: 0 rows
    • auth_attempts: 0 rows
    • system_status: 0 rows
    • cache_entries: 0 rows
    • system_logs: 0 rows

#### API_KEYS
- 파일 수: 2개
- 총 크기: 32.0KB
  - instance/api_keys.db: 16.0KB
    • api_keys: 1 rows
  - data/api_keys.db: 16.0KB
    • api_keys: 0 rows

#### MONITORING
- 파일 수: 2개
- 총 크기: 40.0KB
  - monitoring/deployment_monitoring.db: 20.0KB
    • deployment_events: 0 rows
    • sqlite_sequence: 0 rows
    • metrics: 0 rows
    • system_status: 0 rows
  - data_backup/deployment_monitoring.db: 20.0KB
    • deployment_events: 0 rows
    • sqlite_sequence: 0 rows
    • metrics: 0 rows
    • system_status: 0 rows

#### COLLECTION
- 파일 수: 2개
- 총 크기: 172.0KB
  - data/collection_config.db: 48.0KB
    • collection_sources: 0 rows
    • collection_credentials: 0 rows
    • collection_settings: 0 rows
    • collection_history: 0 rows
    • sqlite_sequence: 0 rows
  - instance/secudium.db: 124.0KB
    • blacklist_ip: 0 rows
    • sqlite_sequence: 0 rows
    • ip_detection: 0 rows
    • daily_stats: 0 rows
    • sqlite_stat1: 0 rows

## ✅ 통합 결과

### 통합된 데이터베이스
- 총 1개 데이터베이스 통합
- 대상 디렉토리: instance/

### 정리된 파일
- 총 8개 중복 파일 삭제
- 백업 위치: db_backup_20250828_123753/

## 📁 최종 구조
```
instance/
├── blacklist.db     # 메인 블랙리스트 DB
├── api_keys.db      # API 키 관리 DB
├── monitoring.db    # 모니터링 데이터 DB
└── collection.db    # 수집 설정 DB
```

## 🎯 추가 권장사항

1. **Git 커밋**
   ```bash
   git add -A
   git commit -m "feat: consolidate database files into single location"
   ```

2. **백업 확인**
   - 백업 디렉토리: `db_backup_20250828_123753/`
   - 30일 후 백업 삭제 권장

3. **코드 업데이트**
   - DB 경로 참조 코드 확인 및 업데이트
   - 테스트 실행으로 검증

---
*Real Automation System v11.1에 의해 자동 생성*
