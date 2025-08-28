# registry.jclee.me 직접 배포 가이드

## 개요

이 가이드는 registry.jclee.me로의 직접 푸시 및 Watchtower 자동 배포 프로세스를 설명합니다.

## 배포 방법

### 1. 전체 워크플로우 실행 (권장)

```bash
# 완전 자동화된 배포 워크플로우
make registry-workflow
```

### 2. 단계별 배포

```bash
# 1단계: 빌드 및 푸시
make registry-deploy

# 2단계: 배포 상태 확인
make registry-verify
```

### 3. 수동 스크립트 실행

```bash
# 직접 스크립트 실행
./scripts/build-and-push.sh
./scripts/verify-registry-deployment.sh
./scripts/registry-deploy-workflow.sh
```

## 배포 구성 요소

### Docker 이미지

1. **메인 애플리케이션**: `registry.jclee.me/blacklist:v1.3.4`
2. **Redis**: `registry.jclee.me/blacklist-redis:v1.3.4`
3. **PostgreSQL**: `registry.jclee.me/blacklist-postgresql:v1.3.4`

### 태그 전략

- `latest`: 최신 안정 버전
- `v1.3.4`: 특정 버전 태그
- `{git-hash}`: Git 커밋 해시 태그

## 자동 배포 프로세스

### Watchtower 동작 방식

1. **이미지 감지**: 5분마다 레지스트리에서 새 이미지 확인
2. **자동 업데이트**: `latest` 태그가 업데이트되면 자동 배포
3. **Graceful Shutdown**: 기존 컨테이너 안전 종료
4. **헬스체크**: 새 컨테이너 정상 동작 확인

### 배포 순서

```
1. 이미지 빌드 → 2. registry.jclee.me 푸시 → 3. Watchtower 감지 → 
4. 컨테이너 재시작 → 5. 헬스체크 → 6. 배포 완료
```

## 모니터링

### 실시간 모니터링 명령어

```bash
# Watchtower 로그 모니터링
docker logs watchtower -f

# 컨테이너 상태 확인
watch -n 5 'docker ps | grep blacklist'

# 애플리케이션 로그
docker logs blacklist -f

# 헬스체크 모니터링
watch -n 10 'curl -s https://blacklist.jclee.me/health | jq .'
```

### 확인 링크

- **라이브 시스템**: https://blacklist.jclee.me/
- **헬스체크**: https://blacklist.jclee.me/health
- **API 상태**: https://blacklist.jclee.me/api/health
- **대시보드**: https://blacklist.jclee.me/dashboard
- **버전 정보**: https://blacklist.jclee.me/api/version

## K8s 지원

### 매니페스트 생성

배포 시 K8s 매니페스트가 자동 생성됩니다:

```bash
k8s-manifests/deployment-v1.3.4.yaml
```

### K8s 배포 (선택사항)

```bash
# K8s 클러스터에 배포
kubectl apply -f k8s-manifests/deployment-v1.3.4.yaml
```

## 주의사항

### AI 제한사항

- **운영서버 직접 접근 불가**: AI는 실제 운영서버에 접근할 수 없음
- **간접 확인만 가능**: 헬스체크 등은 간접적으로만 확인
- **수동 검증 필요**: 실제 배포 상태는 수동으로 확인해야 함

### 레지스트리 인증

- **사용자**: admin
- **비밀번호**: bingogo1
- **레지스트리**: registry.jclee.me

### 버전 관리

- 현재 버전: **v1.3.4**
- VERSION 파일: `config/VERSION`
- Git 태그와 일치 유지 필요

## 트러블슈팅

### 일반적인 문제

1. **이미지 푸시 실패**
   ```bash
   # 레지스트리 로그인 재시도
   docker login registry.jclee.me -u admin
   ```

2. **Watchtower 감지 안됨**
   ```bash
   # Watchtower 재시작
   docker restart watchtower
   ```

3. **헬스체크 실패**
   ```bash
   # 컨테이너 로그 확인
   docker logs blacklist
   ```

### 수동 배포 (비상시)

```bash
# Docker Compose로 수동 배포
cd deployments/docker-compose
docker-compose pull
docker-compose up -d
```

## 관련 파일

- `scripts/build-and-push.sh`: 빌드 및 푸시 스크립트
- `scripts/verify-registry-deployment.sh`: 배포 확인 스크립트
- `scripts/registry-deploy-workflow.sh`: 전체 워크플로우 스크립트
- `deployments/docker-compose/docker-compose.yml`: Docker Compose 설정
- `build/docker/Dockerfile`: 메인 Dockerfile
- `docker/redis/Dockerfile`: Redis Dockerfile
- `docker/postgresql/Dockerfile`: PostgreSQL Dockerfile

---

> **참고**: 이 가이드는 v1.3.4 기준으로 작성되었습니다. 버전 업데이트 시 VERSION 파일과 스크립트를 함께 업데이트하세요.