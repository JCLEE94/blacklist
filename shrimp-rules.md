# Blacklist 프로젝트 개발 가이드라인 (AI Agent 전용)

## 프로젝트 개요

**Blacklist Management System** - 위협 인텔리전스 플랫폼
- **기술 스택**: Python 3.x, Flask 2.3.3, SQLite, Redis, Docker, Kubernetes, ArgoCD
- **아키텍처**: 의존성 주입 (DI), GitOps, 마이크로서비스, 플러그인 시스템
- **네임스페이스**: `blacklist`
- **포트**: DEV=8541, PROD=2541, NodePort=32542

## 프로젝트 아키텍처

### 필수 디렉토리 구조
```
blacklist/
├── src/
│   ├── core/           # 핵심 비즈니스 로직
│   ├── config/         # 환경별 설정
│   ├── utils/          # 유틸리티 함수
│   ├── services/       # 서비스 계층
│   └── web/           # 웹 라우트
├── k8s/               # Kubernetes 매니페스트
├── scripts/           # 배포 및 유틸리티 스크립트
├── deployment/        # Docker 및 배포 설정
└── tests/            # 테스트 코드
```

## 코드 표준

### Python 코드 작성 규칙
- **모든 Python 파일은 UTF-8 인코딩 사용**
- **클래스명은 PascalCase, 함수명은 snake_case 사용**
- **모든 모듈은 docstring으로 시작**
- **타입 힌트 필수 사용**
- **최대 라인 길이 88자 (Black 표준)**

### 필수 import 순서
1. 표준 라이브러리
2. 서드파티 라이브러리
3. 로컬 모듈
```python
import os
import logging
from typing import Dict, Optional

from flask import Flask
import pandas as pd

from src.core.container import get_container
```

## 기능 구현 표준

### 새 API 엔드포인트 추가 시
1. **반드시 `src/core/unified_routes.py`에 추가**
2. **동일한 기능은 `src/web/routes.py`에도 동기화**
3. **응답 형식은 `src/services/response_builder.py` 사용**
4. **캐시 적용 시 `ttl=` 파라미터명 사용 (timeout= 금지)**

### 데이터베이스 작업
- **모든 DB 작업은 `src/core/database.py`의 함수 사용**
- **직접 SQL 실행 금지, SQLAlchemy ORM 사용**
- **마이그레이션은 `init_database.py` 수정**

### 컬렉터 추가 시
1. **`src/core/ip_sources/sources/`에 새 소스 파일 생성**
2. **`BaseIPSource` 클래스 상속 필수**
3. **`collect_ips()` 메서드 구현**
4. **날짜는 원본 데이터의 날짜 사용 (현재 시간 사용 금지)**

## 프레임워크/라이브러리 사용 표준

### Flask 애플리케이션
- **앱 생성은 `src/core/app_compact.py` 사용**
- **라우트 등록은 Blueprint 사용**
- **에러 핸들러는 `src/utils/error_handler.py` 활용**

### 의존성 주입
- **모든 서비스는 `src/core/container.py`에 등록**
- **직접 인스턴스 생성 금지**
```python
# 올바른 방법
container = get_container()
service = container.get('blacklist_manager')

# 잘못된 방법
service = BlacklistManager()  # 금지!
```

### Redis 캐싱
- **`src/utils/advanced_cache.py`의 `CacheManager` 사용**
- **Redis 연결 실패 시 메모리 캐시로 자동 폴백**
- **캐시 키는 `prefix:key` 형식 사용**

## 워크플로우 표준

### Git 브랜치 전략
- **main 브랜치에 직접 푸시**
- **기능별 브랜치 생성 불필요 (GitOps 자동 배포)**

### CI/CD 파이프라인
1. **코드 푸시 → GitHub Actions 자동 실행**
2. **Docker 이미지 빌드 → registry.jclee.me 푸시**
3. **ArgoCD Image Updater가 자동 감지 및 배포**

### 배포 프로세스
- **수동 배포 금지, ArgoCD 자동 동기화 사용**
- **긴급 배포 필요 시 `scripts/k8s-management.sh deploy` 사용**

## 주요 파일 상호작용 표준

### 설정 파일 동기화
- **.env 수정 시 `deployment/docker-compose.yml` 환경변수도 업데이트**
- **`k8s/configmap.yaml` 수정 시 `k8s/secret.yaml` 확인**
- **포트 변경 시 다음 파일 모두 수정:**
  - `main.py`
  - `deployment/docker-compose.yml`
  - `k8s/service.yaml`
  - `k8s/ingress.yaml`

### 문서 업데이트
- **API 변경 시 `CLAUDE.md`의 API Endpoints Reference 섹션 업데이트**
- **새 스크립트 추가 시 `scripts/README.md` 업데이트**
- **배포 관련 변경 시 `docs/GITOPS_QUICK_REFERENCE.md` 확인**

## AI 의사결정 표준

### 코드 수정 우선순위
1. **기존 파일 수정 > 새 파일 생성**
2. **기존 패턴 따르기 > 새로운 패턴 도입**
3. **의존성 주입 사용 > 직접 인스턴스 생성**

### 디버깅 접근법
1. **로그 확인: `docker logs blacklist -f`**
2. **파드 상태: `kubectl get pods -n blacklist`**
3. **ArgoCD 상태: `argocd app get blacklist --grpc-web`**

### 성능 최적화 결정
- **응답 시간 50ms 초과 시 캐싱 적용 검토**
- **메모리 사용량 500MB 초과 시 코드 최적화**
- **동시 요청 100개 이상 처리 가능하도록 설계**

## 금지 사항

### 절대 하지 말아야 할 것들
- **❌ `asyncio.run()` 함수 내부 사용 (main 블록에서만 허용)**
- **❌ 직접 SQL 쿼리 실행**
- **❌ 환경변수 없이 하드코딩된 인증 정보**
- **❌ 수동 Kubernetes 리소스 수정 (kubectl edit 금지)**
- **❌ 현재 시간을 감지 날짜로 사용**
- **❌ try/except로 필수 패키지 import 감싸기**
- **❌ 캐시 데코레이터에 timeout= 파라미터 사용**
- **❌ 프로덕션에서 debug=True 설정**
- **❌ Git에 .env 파일 커밋**
- **❌ 테스트 없이 main 브랜치에 푸시**

### 보안 관련 금지사항
- **❌ 로그에 비밀번호나 토큰 출력**
- **❌ 예외 메시지에 민감한 정보 포함**
- **❌ CORS 설정에서 모든 origin 허용 (`*`)**
- **❌ SQL 인젝션 가능한 쿼리 작성**

## 테스트 작성 규칙

### 단위 테스트
- **pytest 사용, 파일명은 `test_*.py`**
- **각 함수마다 최소 3개 테스트 케이스 (정상, 에지, 에러)**
- **Mock 사용 시 `unittest.mock` 활용**

### 통합 테스트
- **`tests/integration/` 디렉토리에 작성**
- **실제 데이터베이스 연결 테스트 포함**
- **외부 API 호출은 Mock 처리**

## 모니터링 및 로깅

### 로깅 규칙
```python
from loguru import logger

# 정보성 로그
logger.info(f"작업 시작: {task_name}")

# 에러 로그 (스택 트레이스 포함)
logger.error(f"작업 실패: {error}", exc_info=True)
```

### 메트릭 수집
- **응답 시간은 `src/utils/performance.py` 활용**
- **비즈니스 메트릭은 `/api/stats` 엔드포인트에 추가**

## 긴급 상황 대응

### 서비스 장애 시
1. `kubectl logs -f deployment/blacklist -n blacklist` 로그 확인
2. `kubectl rollout restart deployment/blacklist -n blacklist` 재시작
3. `argocd app rollback blacklist --grpc-web` 이전 버전 롤백

### 데이터 손실 시
1. `instance/blacklist.db` 백업 확인
2. `python3 init_database.py --force` 데이터베이스 재생성
3. 백업에서 복원 또는 컬렉터 재실행

## 프로젝트별 특수 규칙

### REGTECH/SECUDIUM 컬렉터
- **세션 기반 인증 사용, 토큰 재사용 금지**
- **날짜 파라미터는 YYYYMMDD 형식 사용**
- **Excel 파일에서 원본 날짜 추출 필수**

### FortiGate 연동
- **`/api/fortigate` 응답은 정확한 JSON 형식 유지**
- **IP 목록은 중복 제거 후 정렬**
- **응답 크기 10MB 초과 시 페이징 적용**

### ArgoCD 설정
- **이미지 태그는 latest, sha-{hash}, date-{timestamp} 사용**
- **자동 동기화 활성화 상태 유지**
- **Health check 실패 시 자동 롤백 설정**