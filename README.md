# Blacklist Management System

엔터프라이즈급 위협 인텔리전스 플랫폼 - 다중 소스 데이터 수집, 자동화된 처리 및 FortiGate External Connector 통합

## 🚀 주요 기능

- **다중 소스 통합**: REGTECH, SECUDIUM 등 여러 위협 인텔리전스 소스 통합
- **자동화된 수집**: 예약된 수집 및 실시간 업데이트
- **FortiGate 연동**: External Connector API를 통한 직접 통합
- **성능 최적화**: Redis 캐싱, 비동기 처리
- **컨테이너화**: Docker 기반 배포 및 Watchtower 자동 업데이트

## 📋 요구사항

- Python 3.9+
- Docker & Docker Compose
- Redis
- Git

## 🛠️ 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/qws941/blacklist.git
cd blacklist

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 실제 값으로 수정
```

### 2. 로컬 개발

```bash
# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 초기화
python3 setup_database.py

# 개발 서버 실행
python3 main.py
```

### 3. Docker 배포

```bash
# Docker Compose로 실행
cd deployment
docker-compose up -d

# 상태 확인
docker-compose ps
docker-compose logs -f
```

### 4. 프로덕션 배포

```bash
# 프로덕션 서버에서 실행
./production-setup.sh
```

## 🔧 환경 변수

주요 환경 변수 설정 (`.env` 파일):

```bash
# Docker Registry
DOCKER_REGISTRY=registry.jclee.me
IMAGE_NAME=blacklist
APP_PORT=2541

# 외부 서비스 인증
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password
SECUDIUM_USERNAME=your-username
SECUDIUM_PASSWORD=your-password

# Redis
REDIS_URL=redis://redis:6379/0
```

전체 환경 변수 목록은 [.env.example](.env.example) 참조

## 📦 프로젝트 구조

```
blacklist/
├── src/                    # 소스 코드
│   ├── core/              # 핵심 비즈니스 로직
│   ├── config/            # 설정 관리
│   ├── utils/             # 유틸리티 함수
│   └── web/               # 웹 라우트
├── deployment/            # 배포 관련 파일
│   ├── docker-compose.yml # Docker Compose 설정
│   ├── Dockerfile         # Docker 이미지 빌드
│   └── docker-compose.watchtower.yml  # Watchtower 설정
├── config/                # 애플리케이션 설정
│   ├── environments.yml   # 환경별 설정
│   └── deployment.yml     # 배포 설정
├── scripts/               # 유틸리티 스크립트
├── tests/                 # 테스트 코드
└── .github/workflows/     # CI/CD 파이프라인
```

## 🚢 배포 방식

### Watchtower 자동 배포

이 프로젝트는 Watchtower를 통한 자동 배포를 사용합니다:

1. **이미지 푸시**: GitHub Actions가 새 Docker 이미지를 `registry.jclee.me`에 푸시
2. **자동 감지**: Watchtower가 30초마다 새 이미지 확인
3. **자동 업데이트**: 새 이미지 발견 시 자동으로 컨테이너 재시작

### CI/CD 파이프라인

```yaml
main 브랜치 푸시 → 테스트 → 빌드 → 레지스트리 푸시 → Watchtower 자동 배포 → 검증
```

## 📊 API 엔드포인트

### 핵심 엔드포인트

- `GET /health` - 시스템 헬스 체크
- `GET /api/blacklist/active` - 활성 IP 목록 (텍스트)
- `GET /api/fortigate` - FortiGate External Connector 형식
- `GET /api/stats` - 시스템 통계

### 수집 관리

- `GET /api/collection/status` - 수집 상태
- `POST /api/collection/enable` - 수집 활성화
- `POST /api/collection/disable` - 수집 비활성화

### 검색 및 분석

- `GET /api/search/{ip}` - 단일 IP 조회
- `POST /api/search` - 배치 IP 검색
- `GET /api/stats/detection-trends` - 탐지 동향

## 🛡️ FortiGate 설정

### External Connector 설정
1. **Connector Type**: `HTTP`
2. **URL**: `http://your-server:2541/api/fortigate`
3. **Update Interval**: `5분`
4. **Format**: `JSON`

### 기존 텍스트 연동
- **URL**: `http://your-server:2541/api/blacklist/active`
- **Format**: `Text (one IP per line)`

## 🔒 보안

- 모든 민감한 정보는 환경 변수로 관리
- GitHub Secrets를 통한 CI/CD 인증 정보 보호
- Docker 레지스트리 인증 필수
- 프로덕션 환경에서 HTTPS 사용 권장

## 🛠️ 개발

### 테스트 실행

```bash
# 전체 테스트
pytest

# 특정 테스트
pytest tests/test_blacklist_unified.py

# 커버리지 포함
pytest --cov=src
```

### 코드 품질

```bash
# 포맷팅
black src/

# 린팅
flake8 src/

# 보안 검사
bandit -r src/
```

## 📈 성능 및 확장성

### 기술 스택
- **Backend**: Flask + Gunicorn
- **Database**: SQLite (개발) / PostgreSQL (프로덕션 옵션)
- **Cache**: Redis
- **Container**: Docker/Podman
- **CI/CD**: GitHub Actions + Self-hosted Runner

### 성능 최적화
- **압축**: 자동 gzip 응답 압축
- **캐싱**: Redis TTL 기반 캐싱
- **Rate Limiting**: 엔드포인트별 제한
- **Connection Pooling**: 데이터베이스 연결 풀링

## 📝 라이선스

이 프로젝트는 비공개 소프트웨어입니다. 무단 복제 및 배포를 금지합니다.

## 🤝 기여

1. 이슈를 생성하여 논의
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'feat: add amazing feature'`)
4. 브랜치 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성

## 📞 지원

- 이슈 트래커: [GitHub Issues](https://github.com/qws941/blacklist/issues)
- 문서: [docs/](./docs/) 디렉토리 참조

---

**현재 버전**: v3.0.0  
**마지막 업데이트**: 2025.06.25