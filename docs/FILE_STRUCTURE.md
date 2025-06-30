# 파일 구조 및 용도

이 문서는 프로젝트의 파일 구조와 각 파일의 용도를 설명합니다.

## 📂 루트 디렉토리

| 파일/디렉토리 | 용도 | 상태 |
|--------------|------|------|
| `main.py` | 애플리케이션 진입점, `app_compact.py`로 위임 | ✅ 활성 |
| `init_database.py` | 데이터베이스 초기화 스크립트 | ✅ 활성 |
| `requirements.txt` | 프로덕션 의존성 | ✅ 활성 |
| `requirements-dev.txt` | 개발용 의존성 | ✅ 활성 |
| `CLAUDE.md` | Claude Code 개발자 가이드 | ✅ 활성 |
| `README.md` | 프로젝트 문서화 | ✅ 활성 |
| `.gitignore` | Git 무시 파일 목록 | ✅ 활성 |

## 📂 소스 코드 (`src/`)

### 핵심 모듈 (`src/core/`)

| 파일 | 용도 | 상태 |
|------|------|------|
| `app_compact.py` | 메인 애플리케이션, Flask 앱 생성 및 설정 | ✅ 활성 |
| `unified_routes.py` | 통합 라우트, 모든 API 엔드포인트 정의 | ✅ 활성 |
| `unified_service.py` | 통합 서비스, 비즈니스 로직 중앙화 | ✅ 활성 |
| `blacklist_unified.py` | 블랙리스트 관리 핵심 로직 | ✅ 활성 |
| `container.py` | 의존성 주입 컨테이너 | ✅ 활성 |
| `collection_manager.py` | 수집 관리 중앙 제어 | ✅ 활성 |
| `settings_routes.py` | 설정 관리 API | ✅ 활성 |
| `v2_routes.py` | 고급 V2 API | ✅ 활성 |
| `regtech_collector.py` | REGTECH 데이터 수집기 (메인) | ✅ 활성 |
| `regtech_collector_enhanced.py` | REGTECH 향상된 수집기 | ✅ 활성 |
| `secudium_collector.py` | SECUDIUM 데이터 수집기 (메인) | ✅ 활성 |
| `har_based_regtech_collector.py` | HAR 기반 REGTECH 수집기 (백업) | ✅ 활성 |
| `har_based_secudium_collector.py` | HAR 기반 SECUDIUM 수집기 (백업) | ✅ 활성 |
| `minimal_app.py` | 최소 기능 백업 앱 | ✅ 활성 |
| `simple_api.py` | 단순 API 백업 | ✅ 활성 |

### 설정 관리 (`src/config/`)

| 파일 | 용도 | 상태 |
|------|------|------|
| `settings.py` | 기본 애플리케이션 설정 | ✅ 활성 |
| `sources.json` | IP 소스 설정 파일 | ✅ 활성 |
| `base.py`, `production.py`, `development.py` | 환경별 설정 | ✅ 활성 |

### 데이터 모델 (`src/models/`)

| 파일 | 용도 | 상태 |
|------|------|------|
| `settings.py` | 설정 데이터 모델 및 관리자 클래스 | ✅ 활성 |

### 유틸리티 (`src/utils/`)

| 파일 | 용도 | 상태 |
|------|------|------|
| `advanced_cache.py` | 고급 캐싱 시스템 (Redis + 메모리 폴백) | ✅ 활성 |
| `performance.py` | 성능 최적화 유틸리티 | ✅ 활성 |
| `structured_logging.py` | 구조화된 로깅 시스템 | ✅ 활성 |
| `error_handler.py` | 통합 에러 처리 | ✅ 활성 |
| `enhanced_security.py` | 보안 강화 기능 | ✅ 활성 |

## 📂 웹 인터페이스 (`templates/`)

### 활성 템플릿

| 파일 | 용도 | 상태 |
|------|------|------|
| `base.html` | 기본 레이아웃 템플릿 | ✅ 활성 |
| `dashboard.html` | 메인 대시보드 | ✅ 활성 |
| `raw_data_modern.html` | 전체 데이터 조회 (모던 UI) | ✅ 활성 |
| `unified_control.html` | 통합 제어 패널 | ✅ 활성 |
| `statistics.html` | 통계 대시보드 | ✅ 활성 |
| `blacklist_search.html` | IP 검색 인터페이스 | ✅ 활성 |
| `docker_logs.html` | Docker 로그 뷰어 | ✅ 활성 |
| `settings/dashboard.html` | 설정 관리 UI | ✅ 활성 |

### 보조 템플릿

| 파일 | 용도 | 상태 |
|------|------|------|
| `raw_data.html` | 전체 데이터 조회 (클래식 UI) | ⚠️ 보조 |
| `error.html` | 에러 페이지 | ✅ 활성 |

## 📂 배포 관련 (`deployment/`)

| 파일 | 용도 | 상태 |
|------|------|------|
| `Dockerfile` | 멀티스테이지 Docker 빌드 | ✅ 활성 |
| `docker-compose.yml` | 프로덕션 Docker Compose | ✅ 활성 |
| `docker-compose.watchtower.yml` | Watchtower 자동 배포 | ✅ 활성 |
| `docker-compose.single.yml` | 단일 컨테이너 배포 | ⚠️ 보조 |

## 📂 스크립트 (`scripts/`)

### 수집 관련 (`scripts/collection/`)
- REGTECH, SECUDIUM 수집 관련 유틸리티 스크립트들

### 배포 관련 (`scripts/deployment/`)
- 배포 자동화 및 관리 스크립트들

### 분석 관련 (`scripts/analysis/`)
- 데이터 분석 및 디버깅 스크립트들

## 📂 테스트 (`tests/`)

| 파일/디렉토리 | 용도 | 상태 |
|--------------|------|------|
| `test_*.py` | 단위 테스트 파일들 | ✅ 활성 |
| `integration/` | 통합 테스트 | ✅ 활성 |
| `conftest.py` | pytest 설정 | ✅ 활성 |

## 📂 CI/CD (`.github/workflows/`)

| 파일 | 용도 | 상태 |
|------|------|------|
| `build-deploy.yml` | 빌드 및 배포 파이프라인 | ✅ 활성 |

## 📂 아카이브 (`archive/`)

### 폐기된 파일들

| 디렉토리 | 내용 | 상태 |
|----------|------|------|
| `deprecated_files/` | 사용하지 않는 소스 파일들 | 🗄️ 아카이브 |
| `deprecated_templates/` | 사용하지 않는 템플릿들 | 🗄️ 아카이브 |

#### 아카이브된 파일들:
- `collection_control_routes.py` - 통합 라우트로 대체됨
- `collection_routes.py` - 통합 라우트로 대체됨  
- `missing_routes.py` - 통합 라우트로 대체됨
- `regtech_collector_*.py` (여러 버전) - 메인 컬렉터로 통합됨
- `secudium_collector_*.py` (여러 버전) - 메인 컬렉터로 통합됨
- 각종 대시보드 템플릿들 - 메인 대시보드로 통합됨

## 📂 데이터 (`data/`, `instance/`)

### 데이터베이스
- `instance/blacklist.db` - 메인 SQLite 데이터베이스

### 수집 데이터
- `data/regtech/` - REGTECH 수집 데이터
- `data/secudium/` - SECUDIUM 수집 데이터
- `data/exports/` - 내보내기 파일들
- `data/logs/` - 수집 로그

## 🎯 핵심 아키텍처

### 데이터 흐름
1. **진입점**: `main.py` → `app_compact.py`
2. **라우팅**: `unified_routes.py` (모든 API 엔드포인트)
3. **비즈니스 로직**: `unified_service.py` (중앙 서비스)
4. **데이터 관리**: `blacklist_unified.py` (IP 관리)
5. **수집**: `*_collector.py` (소스별 수집기)

### 설정 관리
1. **정적 설정**: `src/config/settings.py`
2. **동적 설정**: `src/models/settings.py` (DB 기반)
3. **설정 API**: `settings_routes.py`
4. **설정 UI**: `templates/settings/dashboard.html`

### 캐싱 레이어
1. **Redis 우선**: 프로덕션 환경
2. **메모리 폴백**: 개발 환경
3. **스마트 캐싱**: 태그 기반 무효화

---

**마지막 업데이트**: 2025.06.30  
**상태**: 정리 완료, 아카이브 시스템 적용됨