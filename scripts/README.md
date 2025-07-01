# 📁 Blacklist 스크립트 통합 가이드

## 🎯 개요

Blacklist 프로젝트의 모든 스크립트가 용도별로 체계적으로 정리되어 있습니다. 플랫폼별, 기능별로 분류되어 있어 필요한 스크립트를 쉽게 찾을 수 있습니다.

## 📂 디렉토리 구조

```
scripts/
├── 🚀 unified-deploy.sh          # 통합 배포 스크립트 (메인 진입점)
├── 🔄 trigger-ci.sh              # CI/CD 파이프라인 테스트 트리거
├── 📊 analysis/                  # 테스트 및 분석 스크립트
├── 🗃️ collection/               # 데이터 수집 스크립트 
├── 🗄️ database/                 # 데이터베이스 관리 스크립트
├── 🖥️ platforms/                # 플랫폼별 배포 스크립트
└── ⚙️ setup/                    # 시스템 설정 스크립트
```

## 🚀 빠른 시작

### 통합 배포 (권장)
```bash
# 통합 배포 스크립트 사용 - 플랫폼 자동 선택
./scripts/unified-deploy.sh

# 특정 플랫폼 배포
./scripts/unified-deploy.sh kubernetes
./scripts/unified-deploy.sh docker
./scripts/unified-deploy.sh production
./scripts/unified-deploy.sh local

# Dry-run 모드
./scripts/unified-deploy.sh kubernetes --dry-run
```

### 레거시 배포 (호환성)
```bash
# Ubuntu 기본 배포
./scripts/deploy.sh

# PowerShell 배포 (Windows)
./scripts/deploy.ps1
```

## 📁 상세 디렉토리 가이드

### 🚀 메인 스크립트

| 파일명 | 설명 | 플랫폼 |
|--------|------|--------|
| `unified-deploy.sh` | **통합 배포 스크립트** (권장) | All |
| `deploy.sh` | Ubuntu 기본 배포 | Linux |
| `deploy.ps1` | Windows PowerShell 배포 | Windows |
| `trigger-ci.sh` | CI/CD 파이프라인 테스트 | All |

### 🖥️ platforms/ - 플랫폼별 배포

#### kubernetes/
- `k8s-management.sh` - Kubernetes 통합 관리
- `auto-update.sh` - 자동 이미지 업데이트
- `run_updater.py` - Python 업데이터

#### docker-desktop/
- `deploy-docker-desktop.sh` - Docker Desktop 배포
- `manage-volumes.sh` - 볼륨 관리
- `create-volume-structure.sh` - 볼륨 구조 생성

#### production/
- `deploy-single-to-production.sh` - 운영 배포
- `setup-watchtower.sh` - Watchtower 설정
- `force-update-production.sh` - 강제 업데이트

#### windows/
- `deploy-windows.bat` - Windows 배치 배포
- `clean-deploy-windows.bat` - Windows 클린 배포
- `init-collection.ps1` - 수집 초기화

### 🗃️ collection/ - 데이터 수집

| 스크립트 | 용도 | 데이터 소스 |
|----------|------|------------|
| `simple_regtech_collector.py` | REGTECH 단순 수집 | REGTECH |
| `secudium_auto_collector.py` | SECUDIUM 자동 수집 | SECUDIUM |
| `import_secudium_excel.py` | 엑셀 파일 가져오기 | SECUDIUM |
| `fix_regtech_auth.py` | REGTECH 인증 수정 | REGTECH |

### 🗄️ database/ - 데이터베이스 관리

#### maintenance/ - 유지보수
- `check_db_schema.py` - 스키마 검사
- `fix_db_simple.py` - 간단한 DB 수정
- `fix_production_db.py` - 운영 DB 수정

#### migration/ - 마이그레이션
- `fix_database.py` - 데이터베이스 수정
- `add_expiration_support.py` - 만료 지원 추가
- `check_detection_dates.py` - 탐지 날짜 확인

#### setup/ - 설정
- `database_cleanup_and_setup.py` - DB 정리 및 설정
- `create_ip_detection_table.py` - 탐지 테이블 생성

### 📊 analysis/ - 분석 및 테스트
- `integration_test_comprehensive.py` - 통합 테스트
- `final_test.py` - 최종 테스트
- `main.py` - 분석용 메인

### ⚙️ setup/ - 시스템 설정
- `github-setup.sh` - GitHub 설정
- `set-github-secrets.sh` - GitHub Secrets 설정
- `setup-webhook.sh` - 웹훅 설정

## 🔄 사용 시나리오

### 1. 새로운 환경 배포
```bash
# 1단계: 통합 배포 스크립트로 플랫폼 선택
./scripts/unified-deploy.sh

# 2단계: 데이터베이스 설정 (필요시)
python3 scripts/database/setup/database_cleanup_and_setup.py

# 3단계: 수집 설정 (선택사항)
python3 scripts/collection/simple_regtech_collector.py
```

### 2. CI/CD 파이프라인 테스트
```bash
# CI/CD 테스트 트리거
./scripts/trigger-ci.sh

# 결과 확인
kubectl get pods -n blacklist
kubectl logs deployment/blacklist -n blacklist
```

### 3. 데이터베이스 문제 해결
```bash
# 스키마 확인
python3 scripts/database/maintenance/check_db_schema.py

# 문제 수정
python3 scripts/database/maintenance/fix_db_simple.py

# 마이그레이션 (필요시)
python3 scripts/database/migration/fix_database.py
```

### 4. 운영 환경 긴급 배포
```bash
# 운영 환경 강제 업데이트
./scripts/platforms/production/force-update-production.sh

# 또는 통합 스크립트 사용
./scripts/unified-deploy.sh production --force
```

## ⚠️ 주의사항

### 📋 실행 권한
```bash
# 모든 쉘 스크립트에 실행 권한 부여
find scripts/ -name "*.sh" -exec chmod +x {} \;
```

### 🔒 보안
- 운영 환경 배포는 신중하게 진행
- GitHub Secrets는 `setup/set-github-secrets.sh`로 관리
- 데이터베이스 수정 전 반드시 백업

### 🔄 업그레이드 경로
```bash
# 레거시에서 통합 스크립트로 마이그레이션
# 기존: ./scripts/k8s/deploy.sh
# 신규: ./scripts/unified-deploy.sh kubernetes

# 기존: ./scripts/docker/deploy.sh  
# 신규: ./scripts/unified-deploy.sh docker
```

## 📞 지원

- **문제 발생 시**: `analysis/integration_test_comprehensive.py` 실행
- **로그 확인**: `kubectl logs deployment/blacklist -n blacklist`
- **상태 확인**: `./scripts/unified-deploy.sh [platform] --dry-run`

---
> 🎯 **권장사항**: 새로운 환경에서는 `unified-deploy.sh`를 사용하여 플랫폼을 자동 선택하고 배포하세요.