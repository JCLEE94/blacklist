# Blacklist Management System

[![CI/CD](https://github.com/JCLEE94/blacklist/actions/workflows/cicd.yml/badge.svg)](https://github.com/JCLEE94/blacklist/actions)
[![Docker](https://img.shields.io/badge/Docker-registry.jclee.me-blue.svg)](https://registry.jclee.me)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-brightgreen.svg)](https://kubernetes.io/)
[![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-orange.svg)](https://argoproj.github.io/argo-cd/)

엔터프라이즈 위협 인텔리전스 플랫폼 - GitOps 기반 배포, 다중 소스 데이터 수집, 자동화된 처리 및 FortiGate External Connector 통합

## 🚀 주요 기능

- **GitOps 배포**: ArgoCD 기반 지속적 배포 및 자동 이미지 업데이트
- **다중 서버 지원**: 로컬 및 원격 Kubernetes 클러스터 병렬 배포  
- **Private Registry 지원**: `registry.jclee.me` 및 GHCR 듀얼 레지스트리 지원
- **자동화된 데이터 수집**: REGTECH, SECUDIUM 등 다중 소스 통합
- **FortiGate 연동**: External Connector API 제공
- **고가용성 아키텍처**: 자동 복구, 상태 모니터링, 성능 최적화
- **통합 CI/CD 파이프라인**: 병렬 테스트, 보안 스캔, 자동 빌드, ArgoCD Image Updater 연동
- **포괄적 테스트 스위트**: 통합 테스트, 성능 벤치마크, Rust 스타일 인라인 테스트

## 📋 빠른 시작

### 1. 환경 설정

```bash
# 환경 변수 파일 생성
cp .env.example .env

# .env 파일 편집하여 필수 값 설정
nano .env

# 환경 변수 로드
source scripts/load-env.sh
```

### 2. Registry 설정

#### Private Registry (registry.jclee.me)
```bash
# 인증 불필요 - 자동으로 설정됨
# CI/CD 파이프라인에서 기본으로 사용
# IPv6 연결 문제 시 네트워크 설정 확인 필요
```

### 3. 배포

```bash
# Kubernetes 배포 (ArgoCD GitOps)
./scripts/k8s-management.sh init    # 초기 설정
./scripts/k8s-management.sh deploy  # 배포

# 다중 서버 배포
./scripts/multi-deploy.sh           # 로컬 + 원격 서버 동시 배포
```

## 🏗️ 아키텍처

```mermaid
graph TB
    subgraph "Data Sources"
        A[REGTECH API]
        B[SECUDIUM API]
        C[Public Threat Intel]
    end
    
    subgraph "Application Core"
        D[Collection Manager]
        E[Blacklist Manager]
        F[Cache Layer]
        G[API Server]
    end
    
    subgraph "Infrastructure"
        H[GitHub Actions]
        I[GHCR]
        J[ArgoCD]
        K[Kubernetes]
    end
    
    subgraph "Consumers"
        L[FortiGate]
        M[Web Dashboard]
        N[API Clients]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> L
    G --> M
    G --> N
    
    H --> I
    I --> J
    J --> K
    K --> G
```

## 🛠️ 기술 스택

- **Backend**: Flask 2.3.3 + Gunicorn
- **Database**: SQLite with auto-migration
- **Cache**: Redis (memory fallback)
- **Container**: Docker / Private Registry (registry.jclee.me)
- **Orchestration**: Kubernetes + ArgoCD
- **CI/CD**: GitHub Actions (Self-hosted runner)
- **Monitoring**: Built-in health checks and metrics

## 📦 주요 스크립트

### 핵심 배포 도구

| 스크립트 | 설명 |
|---------|------|
| `scripts/deploy.sh` | 기본 Kubernetes 배포 |
| `scripts/k8s-management.sh` | ArgoCD GitOps 관리 도구 |
| `scripts/multi-deploy.sh` | 다중 서버 동시 배포 |
| `scripts/load-env.sh` | 환경 변수 로드 |
| `scripts/setup-kubeconfig.sh` | kubectl 설정 도우미 |

### ArgoCD 명령어

```bash
# 애플리케이션 상태 확인
./scripts/k8s-management.sh status

# 수동 동기화
./scripts/k8s-management.sh sync

# 롤백
./scripts/k8s-management.sh rollback

# 로그 확인
./scripts/k8s-management.sh logs
```

## 🔧 개발 환경

### 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 초기화
python3 init_database.py

# 개발 서버 실행
python3 main.py --debug
```

### Docker 실행

```bash
# 이미지 빌드
docker build -f deployment/Dockerfile -t registry.jclee.me/blacklist:latest .

# 컨테이너 실행
docker-compose -f deployment/docker-compose.yml up -d
```

## 📡 API 엔드포인트

### 핵심 엔드포인트

- `GET /` - 웹 대시보드
- `GET /health` - 시스템 상태 확인
- `GET /api/blacklist/active` - 활성 IP 목록 (텍스트)
- `GET /api/fortigate` - FortiGate External Connector 형식

### 수집 관리

- `GET /api/collection/status` - 수집 상태
- `POST /api/collection/enable` - 수집 활성화
- `POST /api/collection/disable` - 수집 비활성화
- `POST /api/collection/regtech/trigger` - REGTECH 수동 수집
- `POST /api/collection/secudium/trigger` - SECUDIUM 수동 수집

### V2 API (Enhanced)

- `GET /api/v2/blacklist/enhanced` - 메타데이터 포함 블랙리스트
- `GET /api/v2/analytics/trends` - 분석 및 트렌드
- `GET /api/v2/sources/status` - 소스별 상세 상태

## 🔒 보안

- Private Registry를 통한 내부 이미지 관리
- 환경 변수를 통한 민감 정보 관리
- Kubernetes Secrets 활용
- 코드 스캔을 통한 보안 검사
- Self-hosted runner로 CI/CD 보안 강화

## 🔄 CI/CD 파이프라인

### 통합 파이프라인 (`.github/workflows/cicd.yml`)

- **병렬 실행**: 코드 품질(lint/security) 및 테스트(unit/integration) 병렬 처리
- **자동 취소**: 동일 브랜치에서 새 푸시 시 기존 실행 자동 취소
- **스킵 조건**: 문서만 변경 시 빌드 생략
- **재시도 로직**: ArgoCD 배포 3회 재시도, Health check 5회 재시도
- **Private Registry**: `registry.jclee.me` 기본 사용 (인증 불필요)

### 워크플로우 구조
```yaml
1. Pre-check → 2. Code Quality (병렬) → 3. Tests (병렬) → 4. Build & Push → 5. ArgoCD Image Updater
```

### 수동 배포 스킵
```bash
# GitHub Actions UI에서 workflow_dispatch 실행 시
# skip_tests: true 선택하여 긴급 배포 가능
```

## 📊 모니터링

### 상태 확인

```bash
# Pod 상태
kubectl get pods -n blacklist

# 배포 상태
kubectl get deployment blacklist -n blacklist

# 서비스 상태
curl https://blacklist.jclee.me/health

# CI/CD 파이프라인 상태
gh run list --workflow=cicd.yml --limit=5

# 통합 테스트 실행
python3 tests/integration/run_integration_tests.py

# 성능 벤치마크
python3 tests/integration/performance_benchmark.py
```

### ArgoCD 대시보드

- URL: https://argo.jclee.me
- Application: blacklist
- Image Updater: 2분마다 새 이미지 체크

## 🚨 문제 해결

### 일반적인 문제

1. **이미지 풀 실패**
   ```bash
   # Registry 연결 확인
   curl -v http://registry.jclee.me/v2/
   # Pod 이벤트 확인
   kubectl describe pod <pod-name> -n blacklist
   ```

2. **ArgoCD 동기화 실패**
   ```bash
   # 강제 동기화
   ./scripts/k8s-management.sh sync --force
   ```

3. **Pod 재시작**
   ```bash
   ./scripts/k8s-management.sh restart
   ```

## 📝 환경 변수

필수 환경 변수는 `.env.example` 파일을 참조하세요:

- `REGTECH_USERNAME/PASSWORD`: REGTECH 인증 정보
- `SECUDIUM_USERNAME/PASSWORD`: SECUDIUM 인증 정보
- `ARGOCD_SERVER`: ArgoCD 서버 주소
- `REGISTRY`: Private registry 주소 (기본: registry.jclee.me)

## 🤝 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 감사의 말

- [ArgoCD](https://argoproj.github.io/argo-cd/) - GitOps 도구
- [Kubernetes](https://kubernetes.io/) - 컨테이너 오케스트레이션
- [Docker](https://www.docker.com/) - 컨테이너화 플랫폼# GitOps Pipeline Test 2025. 07. 14. (월) 16:52:28 KST
