# 단일 컨테이너 배포 가이드

## 개요

Blacklist 애플리케이션을 단일 컨테이너로 실행하는 방법입니다. Redis를 별도 컨테이너로 사용하는 대신, 메모리 캐시를 사용하거나 Redis를 내장할 수 있습니다.

## 배포 옵션

### 1. 메모리 캐시 모드 (권장)
Redis 없이 순수 메모리 캐시를 사용합니다. 가장 간단하고 리소스를 적게 사용합니다.

```bash
# 메모리 캐시 모드로 배포
./deploy-single.sh --no-redis

# 또는 docker-compose 직접 사용
docker-compose -f docker-compose.single.yml up -d
```

**장점:**
- 단일 프로세스로 실행
- 메모리 사용량 최소화
- 설정이 간단함
- 컨테이너 재시작 시 빠른 시작

**단점:**
- 컨테이너 재시작 시 캐시 손실
- 대용량 캐시 저장 불가

### 2. Redis 내장 모드
Supervisor를 사용하여 하나의 컨테이너에서 Redis와 Flask 앱을 함께 실행합니다.

```bash
# Redis 내장 모드로 배포
./deploy-single.sh --with-redis
```

**장점:**
- 여전히 단일 컨테이너
- Redis의 모든 기능 사용 가능
- 캐시 영속성 (선택적)

**단점:**
- 컨테이너 크기 증가
- 메모리 사용량 증가
- 복잡도 증가

## 직접 Docker 명령어 사용

### 빌드 및 실행 (메모리 캐시)
```bash
# 이미지 빌드
docker build -t blacklist:single -f deployment/Dockerfile.single --target production .

# 컨테이너 실행
docker run -d \
  --name blacklist \
  -p 2541:2541 \
  -v $(pwd)/instance:/app/instance \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e REGTECH_USERNAME=nextrade \
  -e REGTECH_PASSWORD=Sprtmxm1@3 \
  -e SECUDIUM_USERNAME=nextrade \
  -e SECUDIUM_PASSWORD=Sprtmxm1@3 \
  blacklist:single
```

### 빌드 및 실행 (Redis 내장)
```bash
# 이미지 빌드
docker build -t blacklist:single-redis -f deployment/Dockerfile.single --target production-with-redis .

# 컨테이너 실행
docker run -d \
  --name blacklist \
  -p 2541:2541 \
  -v $(pwd)/instance:/app/instance \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e REGTECH_USERNAME=nextrade \
  -e REGTECH_PASSWORD=Sprtmxm1@3 \
  -e SECUDIUM_USERNAME=nextrade \
  -e SECUDIUM_PASSWORD=Sprtmxm1@3 \
  blacklist:single-redis
```

## 관리 명령어

### 로그 확인
```bash
# 전체 로그
docker logs -f blacklist

# Redis 내장 모드에서 개별 프로세스 로그
docker exec blacklist tail -f /app/logs/blacklist.log
docker exec blacklist tail -f /app/logs/redis.log
```

### 상태 확인
```bash
# 헬스 체크
curl http://localhost:2541/health

# 통계 확인
curl http://localhost:2541/api/stats

# 컨테이너 상태
docker ps | grep blacklist
docker stats blacklist
```

### 재시작
```bash
# 컨테이너 재시작
docker restart blacklist

# 완전히 재배포
./deploy-single.sh --no-redis
```

## 프로덕션 배포

프로덕션 서버(192.168.50.215)에 배포하려면:

1. 이미지를 레지스트리에 푸시
```bash
docker tag blacklist:single 192.168.50.215:1234/blacklist:single-latest
docker push 192.168.50.215:1234/blacklist:single-latest
```

2. 프로덕션 서버에서 실행
```bash
# SSH 접속
ssh docker@192.168.50.215 -p 1111

# 기존 컨테이너 정지
docker stop blacklist-app blacklist-redis || true
docker rm blacklist-app blacklist-redis || true

# 새 컨테이너 실행
docker run -d \
  --name blacklist \
  --restart unless-stopped \
  -p 2541:2541 \
  -v /opt/blacklist/instance:/app/instance \
  -v /opt/blacklist/data:/app/data \
  -v /opt/blacklist/logs:/app/logs \
  -e REGTECH_USERNAME=nextrade \
  -e REGTECH_PASSWORD='Sprtmxm1@3' \
  -e SECUDIUM_USERNAME=nextrade \
  -e SECUDIUM_PASSWORD='Sprtmxm1@3' \
  192.168.50.215:1234/blacklist:single-latest
```

## 성능 비교

| 항목 | 멀티 컨테이너 | 메모리 캐시 | Redis 내장 |
|------|--------------|------------|------------|
| 컨테이너 수 | 2 | 1 | 1 |
| 메모리 사용량 | ~200MB | ~100MB | ~150MB |
| 시작 시간 | 10초 | 5초 | 8초 |
| 캐시 영속성 | ✓ | ✗ | ✓ |
| 복잡도 | 중간 | 낮음 | 높음 |

## 문제 해결

### 포트 충돌
```bash
# 사용 중인 포트 확인
sudo lsof -i :2541

# 다른 포트로 실행
docker run -p 8541:2541 ...
```

### 권한 문제
```bash
# 볼륨 권한 설정
sudo chown -R 1000:1000 ./instance ./data ./logs
```

### 메모리 부족
```bash
# 메모리 제한 설정
docker run --memory="512m" --memory-swap="1g" ...
```

## 추천 설정

대부분의 경우 **메모리 캐시 모드**를 권장합니다:
- 설정이 간단함
- 리소스 사용량이 적음
- 캐시는 주로 성능 향상용이므로 손실되어도 문제없음
- 블랙리스트 데이터는 SQLite에 영구 저장됨

Redis가 꼭 필요한 경우만 Redis 내장 모드를 사용하세요.