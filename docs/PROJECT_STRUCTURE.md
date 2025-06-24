# 📁 프로젝트 구조

## 디렉토리 구조

```
blacklist/
├── src/                    # 소스 코드
│   ├── core/              # 핵심 비즈니스 로직
│   ├── api/               # API 엔드포인트
│   ├── config/            # 설정 관리
│   └── utils/             # 유틸리티 함수
├── tests/                  # 테스트 코드
├── scripts/                # 유틸리티 스크립트
├── deployment/             # 배포 관련 파일
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   ├── docker-compose.watchtower.yml
│   └── deploy*.sh
├── docs/                   # 문서
│   ├── reports/           # 분석 리포트
│   └── *.md               # 각종 문서
├── config/                 # 설정 파일
│   └── watchtower-config.json (gitignore)
├── data/                   # 데이터 파일
├── logs/                   # 로그 파일
├── instance/               # Flask 인스턴스 폴더
├── static/                 # 정적 파일
├── templates/              # HTML 템플릿
├── tests_archive/          # 아카이브된 테스트
├── backups/                # 백업 파일
├── main.py                 # 애플리케이션 진입점
├── requirements.txt        # Python 의존성
├── README.md              # 프로젝트 소개
└── CLAUDE.md              # AI 도우미 가이드
```

## 주요 디렉토리 설명

### /src
애플리케이션의 핵심 소스 코드가 위치합니다.
- `core/`: 비즈니스 로직 (blacklist 관리, 수집기 등)
- `api/`: REST API 엔드포인트
- `config/`: 중앙 집중식 설정 관리
- `utils/`: 캐싱, 로깅 등 유틸리티

### /deployment
배포 관련 모든 파일이 위치합니다.
- Docker 관련 파일들
- 배포 스크립트
- docker-compose 설정들

### /docs
프로젝트 문서들이 위치합니다.
- 배포 가이드
- API 문서
- 분석 리포트 (reports/)

### /tests
현재 활성화된 테스트 코드들이 위치합니다.

### /tests_archive
이전 버전이나 임시 테스트 파일들이 보관됩니다.

## 파일 이동 가이드

### 새 파일 생성 시
- Python 소스: `/src` 하위 적절한 디렉토리
- 테스트 코드: `/tests`
- 문서: `/docs`
- 배포 스크립트: `/deployment`
- 설정 파일: `/config`

### 임시 파일
- 로그: `/logs`
- 백업: `/backups`
- 임시 데이터: `/data/temp`

## Git 관리

### .gitignore에 포함된 디렉토리
- `/instance` - Flask 인스턴스 데이터
- `/logs` - 로그 파일
- `/data/temp` - 임시 데이터
- `/config/watchtower-config.json` - 보안 설정
- `/backups` - 백업 파일
- `/document` - 대용량 문서 파일