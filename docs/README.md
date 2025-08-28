# 📚 Blacklist System Documentation

## 🎯 Quick Start
- **[설치 가이드](DEPLOYMENT.md)** - 빠른 설치 및 배포
- **[API 참조](api-reference.md)** - REST API 전체 문서
- **[브랜치 전략](../.github/BRANCH_STRATEGY.md)** - GitOps 워크플로우

## 🏗️ 아키텍처
- **[시스템 개요](../CLAUDE.md)** - 전체 시스템 구조
- **[Docker 구성](../docker-compose.yml)** - 컨테이너 환경
- **[K8s 매니페스트](../deployments/k8s/)** - 쿠버네티스 배포

## 🚀 운영 가이드
- **[GitOps 가이드](GITOPS.md)** - CI/CD 파이프라인
- **[Registry 가이드](REGISTRY_DEPLOYMENT_GUIDE.md)** - 컨테이너 레지스트리
- **[보안 설정](REGISTRY_AUTH_SETUP.md)** - 인증 및 보안

## 🔧 개발자 가이드
- **[기여 가이드](../CONTRIBUTING.md)** - 개발 참여 방법
- **[버전 관리](VERSION_MANAGEMENT.md)** - 릴리즈 프로세스
- **[규칙 문서](rules/shrimp-rules.md)** - 개발 규칙

## 📊 현재 상태
- **버전**: v1.0.1438+
- **환경**: Production Ready
- **상태**: ✅ 활성 운영 중
- **모니터링**: https://blacklist.jclee.me/health

## 📁 디렉토리 구조
```
docs/
├── README.md              # 이 파일
├── api-reference.md       # API 문서
├── DEPLOYMENT.md          # 배포 가이드  
├── GITOPS.md             # GitOps 가이드
├── VERSION_MANAGEMENT.md  # 버전 관리
├── rules/                # 개발 규칙
└── portfolio-content.md   # GitHub Pages 내용
```

---
📅 **최종 업데이트**: 2025-08-28  
🔄 **문서 버전**: v2.0 (현행화 완료)