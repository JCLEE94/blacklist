# K8s 사용 안 함 - 메모 및 기억사항

## 핵심 결정사항
**날짜**: 2025-08-18  
**결정**: Kubernetes(k8s) 사용하지 않음  
**이유**: Docker-Compose로 충분, 복잡성 감소

## 현재 아키텍처
- **컨테이너 관리**: Docker-Compose 전용
- **서비스 구성**:
  - blacklist (Flask 앱): 포트 32542
  - redis (캐시): 내부 통신
- **배포 파이프라인**: GitHub Actions → registry.jclee.me → docker-compose

## 금지된 명령어들
```bash
# 절대 사용 안 함
kubectl apply/get/delete
argo app sync/set  
helm install/upgrade
k9s, kubectx, kubens
```

## 사용할 명령어들
```bash
# Docker-Compose 전용
docker-compose ps              # 서비스 상태
docker-compose pull            # 이미지 업데이트  
docker-compose up -d           # 서비스 시작
docker-compose logs            # 로그 확인
docker-compose restart         # 서비스 재시작
```

## 워크플로우 임팩트
- **`/deploy` 명령**: k8s 대신 Docker-Compose 관리
- **`/main` 워크플로우**: k8s pods 체크 → docker-compose 서비스 체크
- **모든 인프라 에이전트**: Docker-Compose 작업만 수행

## 상태 확인 방법
```bash
# 서비스 헬스체크 (k8s 대신)
docker-compose ps | grep "Up"
curl http://localhost:32542/health

# 로그 분석 (kubectl logs 대신)  
docker-compose logs --tail=100 blacklist
docker-compose logs redis
```

## 주의사항
- 모든 자동화 스크립트에서 k8s 명령어 제거
- Docker-Compose 기반 헬스체크로 변경
- GitOps는 git push → GitHub Actions → docker-compose 방식만 사용