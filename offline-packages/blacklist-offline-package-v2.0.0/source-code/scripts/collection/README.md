# 데이터 수집 스크립트 가이드

## 📁 정리된 수집 스크립트 구조

### 핵심 수집 스크립트 (우선순위별)

#### 🎯 REGTECH 수집
1. **regtech_auto_collector.py** - 브라우저 자동화 (Playwright)
2. **regtech_complete_collector.py** - 완전 수집기 
3. **regtech_data_validator.py** - 데이터 검증
4. **regtech_consolidate_and_import.py** - 통합 및 가져오기

#### 🎯 SECUDIUM 수집  
1. **secudium_auto_collector.py** - OTP 처리 포함 자동화
2. **import_secudium_excel.py** - 엑셀 파일 가져오기
3. **secudium_api_collector.py** - API 기반 수집

### 📊 데이터 흐름

```
원본 수집 → 정제/검증 → 통합 → 데이터베이스 저장
├── scripts/regtech_*collector.py
├── scripts/regtech_data_validator.py  
├── data/cleaned/regtech/
└── instance/blacklist.db
```

### 🗂️ 개선된 데이터 디렉토리 구조

```
data/
├── sources/          # 원본 데이터
│   ├── regtech/
│   └── secudium/
├── cleaned/          # 정제된 데이터
│   ├── regtech/
│   └── secudium/
├── exports/          # 내보내기
└── backups/          # 백업
```

### 🚀 권장 사용법

```bash
# REGTECH 전체 수집 프로세스
python3 scripts/regtech_complete_collector.py --max-pages 5
python3 scripts/regtech_data_validator.py
python3 scripts/regtech_consolidate_and_import.py

# SECUDIUM 수집 (수동 개입 필요)
python3 scripts/secudium_auto_collector.py
python3 scripts/import_secudium_excel.py data/downloads/secudium/latest.xlsx
```

### ⚠️ 중요 사항

- **REGTECH**: 인증 없이 일부 데이터만 수집 가능
- **SECUDIUM**: OTP 인증으로 수동 개입 필요
- **백업**: 매일 자동 백업 (cron 설정됨)
- **검증**: 수집 후 반드시 데이터 검증 실행