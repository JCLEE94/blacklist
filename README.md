# 🛡️ Blacklist Management System v1.0.35

> **Production-Ready** | **GitOps** | **Enterprise** | **Portfolio**

차세대 위협 인텔리전스 플랫폼 - JWT 보안, V2 API, GitHub Pages 포트폴리오 완비

[![Live Demo](https://img.shields.io/badge/Live%20Demo-jclee94.github.io-blue?style=for-the-badge&logo=github-pages)](https://jclee94.github.io/blacklist/)
[![Docker](https://img.shields.io/badge/Docker-registry.jclee.me-2496ED?style=for-the-badge&logo=docker)](https://registry.jclee.me)
[![GitOps](https://img.shields.io/badge/GitOps-9.5%2F10-success?style=for-the-badge)](https://github.com/JCLEE94/blacklist/actions)

---

## 🚀 Quick Start

```bash
# Private Registry
docker run -p 32542:2541 registry.jclee.me/blacklist:latest

# 포트폴리오 사이트 확인
open https://jclee94.github.io/blacklist/

# API 테스트
curl http://localhost:32542/health | jq
curl http://localhost:32542/api/v2/analytics/trends | jq

# 보안 시스템 초기화 (로컬 개발용)
python3 scripts/init_security.py
```

## 📊 시스템 현황

- **포트폴리오**: [`jclee94.github.io/blacklist`](https://jclee94.github.io/blacklist/) (GitHub Pages)
- **컨테이너**: `registry.jclee.me/blacklist` (Private Registry)  
- **아키텍처**: Flask + SQLite + Redis + JWT 보안 시스템
- **수집**: REGTECH/SECUDIUM 자동화 + V2 API 완료
- **배포**: GitOps (Push → GitHub Actions → 자동 배포)

## 🔗 주요 엔드포인트

### 🆕 V2 API (New!)
| URL | 기능 | 상태 |
|-----|------|------|
| `/api/v2/analytics/trends` | 트렌드 분석 | ✅ |
| `/api/v2/analytics/summary` | 분석 요약 | ✅ |
| `/api/v2/sources/status` | 소스 상태 | ✅ |
| `/api/auth/login` | JWT 로그인 | ✅ |
| `/api/keys/verify` | API 키 인증 | ✅ |

### 🔒 Core API
| URL | 기능 | 상태 |
|-----|------|------|
| `/health` | 시스템 상태 | ✅ |
| `/api/blacklist/active` | IP 목록 | ✅ |
| `/api/fortigate` | FortiGate 연동 | ✅ |
| `/statistics` | 통계 대시보드 | ✅ |

## ⚡ 개발 워크플로우

```bash
# 코드 수정 → 자동 배포
git commit -m "feat: 새 기능 추가"
git push origin main
# → GitHub Actions → Docker Build → registry.jclee.me → GitHub Pages
```

## 🏗️ 기술 스택

**Backend**
- Python 3.9 + Flask 2.3.3
- SQLite (dev) / PostgreSQL (prod) 
- Redis 7 (메모리 폴백)
- JWT + API Key 이중 보안

**Frontend & Portfolio**
- GitHub Pages (모던 포트폴리오)
- 반응형 디자인 + 다크 테마
- 실시간 성능 메트릭 차트

**DevOps**
- Private Registry (registry.jclee.me)
- GitHub Actions CI/CD (ubuntu-latest)
- Docker Multi-stage builds
- Automated security scanning (Trivy + Bandit)

**Monitoring**
- Prometheus 55개 메트릭
- 23개 알림 규칙  
- 실시간 대시보드

## 📈 성능 지표

- **응답 시간**: 평균 7.58ms
- **동시 처리**: 100+ 요청
- **테스트 커버리지**: 95%+
- **GitOps 성숙도**: 9.5/10
- **보안 시스템**: JWT + API Key 완전 구현

## 🆕 새로운 기능 (v1.0.35)

### 🎨 GitHub Pages Portfolio
- **라이브 사이트**: https://jclee94.github.io/blacklist/
- 모던 다크 테마 + 그라데이션 애니메이션
- 대화형 성능 메트릭 차트
- 완전한 API 문서 + 아키텍처 다이어그램

### 🔐 JWT + API Key 보안 시스템
```bash
# 자동 초기화
python3 scripts/init_security.py

# API 키 테스트
curl -H "X-API-Key: blk_your-key" http://localhost:32542/api/keys/verify

# JWT 로그인
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  http://localhost:32542/api/auth/login
```

### ✅ V2 API 완전 구현
- Analytics API (6개 엔드포인트)
- Sources API (실시간 상태)
- 통합 캐싱 + 에러 처리
- OpenAPI 문서 자동 생성

## 🔧 개발 환경

```bash
# 환경 설정
make init                          # 프로젝트 초기화
python3 scripts/setup-credentials.py  # 자격증명 설정

# 테스트
pytest -v                          # 전체 테스트 (95% 커버리지)
pytest -m unit                     # 유닛 테스트만
pytest -m api                      # API 테스트만

# 코드 품질
flake8 src/ --count                # 린팅
black src/ tests/                  # 포맷팅
bandit -r src/                     # 보안 스캔

# 로컬 실행
python3 app/main.py --debug       # 개발 서버 (포트 2542)
docker-compose up -d               # Docker 환경 (포트 32542)
```

## 🚢 배포

```bash
# GitHub Container Registry 사용
docker pull ghcr.io/jclee94/blacklist:latest

# 자동 배포 (GitOps)
git push origin main  # GitHub Actions가 자동으로 배포

# 오프라인 패키지 생성
python3 scripts/create-offline-package.py
```

---

**Made with ❤️ by JCLEE** | [Portfolio Demo](https://jclee94.github.io/blacklist/) | [Docker Image](https://registry.jclee.me/blacklist)