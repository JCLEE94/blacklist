# 🛡️ Blacklist Management System v1.0.37

> **Production-Ready** | **GitOps** | **Enterprise** | **Live System**

차세대 위협 인텔리전스 플랫폼 - 실시간 대시보드, 자동 수집 시스템, JWT 보안 완비

[![Live System](https://img.shields.io/badge/Live%20System-blacklist.jclee.me-success?style=for-the-badge&logo=server)](https://blacklist.jclee.me/)
[![Live Demo](https://img.shields.io/badge/Portfolio-jclee94.github.io-blue?style=for-the-badge&logo=github-pages)](https://jclee94.github.io/blacklist/)
[![Docker](https://img.shields.io/badge/Docker-registry.jclee.me-2496ED?style=for-the-badge&logo=docker)](https://registry.jclee.me)
[![GitOps](https://img.shields.io/badge/GitOps-8.5%2F10-success?style=for-the-badge)](https://github.com/JCLEE94/blacklist/actions)

---

## 🚀 Quick Start

### 🌐 Live System Access
```bash
# Production System (Live)
curl https://blacklist.jclee.me/health | jq
curl https://blacklist.jclee.me/api/blacklist/active
open https://blacklist.jclee.me/dashboard

# Portfolio Site
open https://jclee94.github.io/blacklist/
```

### 🐳 Local Development
```bash
# Private Registry
docker run -p 32542:2542 registry.jclee.me/blacklist:latest

# Local API Testing
curl http://localhost:32542/health | jq
curl http://localhost:32542/api/blacklist/active

# Security System Setup
python3 scripts/init_security.py
```

## 📊 Live System Status (v1.0.37)

- **🌐 Live URL**: [`blacklist.jclee.me`](https://blacklist.jclee.me/) - **OPERATIONAL**
- **📊 Portfolio**: [`jclee94.github.io/blacklist`](https://jclee94.github.io/blacklist/) (GitHub Pages)
- **🐳 Container**: `registry.jclee.me/blacklist:latest` (Private Registry)
- **🏗️ Architecture**: Flask + PostgreSQL + Redis + JWT Authentication
- **📡 Collection**: REGTECH/SECUDIUM Automated + Real-time Dashboard
- **🔒 Security**: JWT + API Key dual authentication system
- **🚀 Deployment**: GitOps with GitHub Actions
- **📈 Performance**: 50-65ms response times (excellent)

## 🔗 Live System Endpoints

### 🌐 Core System (Live at blacklist.jclee.me)
| URL | Description | Status |
|-----|-------------|--------|
| [`/health`](https://blacklist.jclee.me/health) | System health check | ✅ LIVE |
| [`/api/blacklist/active`](https://blacklist.jclee.me/api/blacklist/active) | Active IP blacklist | ✅ LIVE |
| [`/api/fortigate`](https://blacklist.jclee.me/api/fortigate) | FortiGate integration | ✅ LIVE |
| [`/dashboard`](https://blacklist.jclee.me/dashboard) | Collection dashboard | ✅ LIVE |
| [`/statistics`](https://blacklist.jclee.me/statistics) | Statistics dashboard | ✅ LIVE |

### 🔒 Authentication & Security
| URL | Description | Status |
|-----|-------------|--------|
| `/api/auth/login` | JWT Authentication | ✅ |
| `/api/keys/verify` | API Key verification | ✅ |
| `/api/collection/status` | Collection status | ✅ |

### 🔒 V2 API & Auth
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

## 📈 Performance Metrics (Live System)

- **⚡ Response Time**: 50-65ms (excellent)
- **🔄 Concurrent Requests**: 100+ supported
- **🧪 Test Coverage**: 19% (improving toward 95% target)
- **🔄 GitOps Maturity**: 8.5/10 (production-ready)
- **🔒 Security**: JWT + API Key authentication validated
- **💾 Database**: PostgreSQL with connection pooling
- **🚀 Deployment**: Automated with GitHub Actions

## 🔍 Live System Features

### 📊 Real-time Threat Intelligence
```bash
# Live System API Testing
curl https://blacklist.jclee.me/health | jq
curl https://blacklist.jclee.me/api/blacklist/active
curl https://blacklist.jclee.me/api/collection/status | jq
```

### 📈 Dashboard System
- **Collection Dashboard** ([`/dashboard`](https://blacklist.jclee.me/dashboard)): Daily collection status, calendar visualization
- **Statistics Dashboard** ([`/statistics`](https://blacklist.jclee.me/statistics)): Real-time analytics and charts
- **System Health**: Real-time monitoring with health checks
- **Performance Metrics**: Response time and system resource tracking

### 🔄 Automated Collection System
- **REGTECH Integration**: Automated threat data collection
- **SECUDIUM Integration**: Secondary threat intelligence source
- **Real-time Processing**: Immediate IP validation and classification
- **Quality Control**: Duplicate removal and threat level classification
- **Progress Tracking**: Real-time collection progress monitoring

## 🆕 Production System Features (v1.0.37)

### 🌐 Live Production System
- **Live URL**: https://blacklist.jclee.me/ - **FULLY OPERATIONAL**
- **High Availability**: Docker Compose with health checks
- **Performance**: 50-65ms response times validated
- **Security**: JWT + API Key authentication working

### 🎨 Portfolio Website
- **Demo Site**: https://jclee94.github.io/blacklist/
- Modern dark theme with responsive design
- Interactive performance metrics charts
- Complete API documentation and architecture diagrams

### 🔐 Security System
```bash
# Live System Security Testing
curl https://blacklist.jclee.me/api/keys/verify
curl -X POST https://blacklist.jclee.me/api/auth/login

# Local Development Setup
python3 scripts/init_security.py
```

### ✅ System Infrastructure
- **Database**: PostgreSQL with connection pooling
- **Cache**: Redis with memory fallback
- **Monitoring**: Health checks and performance metrics
- **Deployment**: GitOps with automated GitHub Actions

## 🔧 Development Environment

### 🌐 Live System Testing
```bash
# Test live production system
curl https://blacklist.jclee.me/health | jq
curl https://blacklist.jclee.me/api/blacklist/active
open https://blacklist.jclee.me/dashboard
```

### 🛠️ Local Development
```bash
# Environment setup
make init                              # Project initialization
python3 scripts/setup-credentials.py  # Credentials setup

# Testing (improving from 19% to 95% target)
pytest -v                              # All tests
pytest -m unit                         # Unit tests only
pytest -m api                          # API tests only
pytest --cov=src --cov-report=html    # Coverage report

# Code quality
flake8 src/ --count                    # Linting
black src/ tests/                      # Formatting
bandit -r src/                         # Security scan

# Local execution
docker-compose up -d                   # Docker environment (port 32542:2542)

# Access dashboards
open http://localhost:32542/dashboard      # Collection dashboard
open http://localhost:32542/statistics     # Statistics dashboard
```

## 🚢 Deployment

### 🌐 Production System
```bash
# Live production system (already deployed)
https://blacklist.jclee.me/

# Registry access
docker pull registry.jclee.me/blacklist:latest

# GitOps deployment
git push origin main  # Triggers GitHub Actions automatic deployment
```

### 🐳 Local Deployment
```bash
# Docker Compose (matches production configuration)
docker-compose up -d

# Health verification
curl http://localhost:32542/health | jq

# Offline package creation
python3 scripts/create-offline-package.py
```

---

**Made with ❤️ by JCLEE** | [Portfolio Demo](https://jclee94.github.io/blacklist/) | [Docker Image](https://registry.jclee.me/blacklist)# Hook 테스트용 코멘트
