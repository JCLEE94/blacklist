# 🛡️ Blacklist Management System

> **Production-Ready** | **GitOps** | **Enterprise**

IP 위협 정보 수집 및 FortiGate 연동 시스템

---

## 🚀 Quick Start

```bash
# 로컬 개발
docker run -p 32542:2541 registry.jclee.me/jclee94/blacklist:latest

# 프로덕션 접근
curl https://blacklist.jclee.me/health
```

## 📊 시스템 현황

- **프로덕션**: `blacklist.jclee.me` (Kubernetes + ArgoCD)
- **아키텍처**: Flask + SQLite + Redis (메모리 폴백)
- **수집**: REGTECH/SECUDIUM 자동화
- **배포**: GitOps (Push → Auto Deploy)

## 🔗 주요 엔드포인트

| URL | 기능 | 상태 |
|-----|------|------|
| `/health` | 시스템 상태 | ✅ |
| `/api/blacklist/active` | IP 목록 | ✅ |
| `/api/fortigate` | FortiGate 연동 | ✅ |
| `/statistics` | 통계 대시보드 | ✅ |

## ⚡ 개발 워크플로우

```bash
# 코드 수정 → 자동 배포
git commit -m "fix: 문제 수정"
git push origin main
# → GitHub Actions → Docker Build → ArgoCD → Production
```

## 🏗️ 기술 스택

**Backend**
- Python 3.11 + Flask 2.3
- SQLite (dev) / PostgreSQL (prod)
- Redis 7 (메모리 폴백)

**DevOps**
- Docker + Kubernetes
- ArgoCD GitOps
- GitHub Actions CI/CD
- Helm Charts

**Monitoring**
- Prometheus 55개 메트릭
- 23개 알림 규칙
- 실시간 대시보드

## 📈 성능 지표

- **응답 시간**: 평균 7.58ms
- **동시 처리**: 100+ 요청
- **테스트 커버리지**: 95%+
- **GitOps 성숙도**: 9/10

## 🔧 개발 환경

```bash
# 테스트
pytest -v                          # 전체 테스트
pytest -m unit                     # 유닛 테스트만

# 코드 품질
flake8 src/ --count                # 린팅
black src/ tests/                  # 포맷팅

# 로컬 실행
python3 app/main.py --debug       # 개발 서버 (포트 8541)
```

---

**Made with ❤️ by JCLEE** | [Live Demo](https://blacklist.jclee.me)