# 🐳 Watchtower 자동 배포 가이드

## 개요

Watchtower를 사용하여 Docker 이미지가 업데이트되면 자동으로 컨테이너를 재시작하는 CI/CD 파이프라인입니다.

## 구성 요소

### 1. docker-compose.watchtower.yml
- **blacklist-app**: 메인 애플리케이션 컨테이너
- **blacklist-redis**: Redis 캐시 서버
- **watchtower**: 자동 업데이트 모니터

### 2. 레지스트리 정보
- **Registry**: registry.jclee.me
- **Image**: registry.jclee.me/blacklist-management:latest
- **Port**: 2541 (호스트) → 8541 (컨테이너)

## 초기 설정

### 1. 자동 설정 (권장)
```bash
./scripts/setup-watchtower.sh
```

### 2. 수동 설정
```bash
# 1. 레지스트리 인증 파일 생성
echo -n "qws941:bingogo1l7!" | base64 > auth.txt
cat > watchtower-config.json << EOF
{
  "auths": {
    "registry.jclee.me": {
      "auth": "$(cat auth.txt)"
    }
  }
}
EOF
rm auth.txt

# 2. 권한 설정
chmod 600 watchtower-config.json

# 3. 컨테이너 시작
docker-compose -f docker-compose.watchtower.yml up -d
```

## 운영 명령어

### 서비스 관리
```bash
# 시작
docker-compose -f docker-compose.watchtower.yml up -d

# 중지
docker-compose -f docker-compose.watchtower.yml down

# 재시작
docker-compose -f docker-compose.watchtower.yml restart

# 상태 확인
docker-compose -f docker-compose.watchtower.yml ps
```

### 로그 확인
```bash
# 전체 로그
docker-compose -f docker-compose.watchtower.yml logs -f

# 애플리케이션 로그
docker logs blacklist-app -f

# Watchtower 로그 (업데이트 확인)
docker logs watchtower -f

# Redis 로그
docker logs blacklist-redis -f
```

### 수동 업데이트
```bash
# 즉시 업데이트 확인
docker exec watchtower /watchtower --run-once

# 특정 컨테이너만 업데이트
docker exec watchtower /watchtower --run-once blacklist-app
```

## 모니터링

### 헬스 체크
```bash
# 애플리케이션 상태
curl http://localhost:2541/health

# API 통계
curl http://localhost:2541/api/stats

# 컨테이너 상태
docker ps | grep blacklist
```

### Watchtower 동작 확인
```bash
# 마지막 업데이트 시간 확인
docker logs watchtower | grep "Checking for available updates"

# 업데이트 이벤트 확인
docker logs watchtower | grep "Found new"
```

## 문제 해결

### 1. 이미지 Pull 실패
```bash
# 레지스트리 연결 테스트
docker pull registry.jclee.me/blacklist-management:latest

# 인증 확인
cat watchtower-config.json | jq .

# 수동 로그인 테스트
docker login registry.jclee.me -u qws941 -p bingogo1l7!
```

### 2. 컨테이너 재시작 실패
```bash
# 기존 컨테이너 제거
docker-compose -f docker-compose.watchtower.yml down
docker system prune -f

# 깨끗한 시작
docker-compose -f docker-compose.watchtower.yml up -d --force-recreate
```

### 3. 네트워크 문제
```bash
# 네트워크 재생성
docker network rm blacklist_blacklist-net
docker-compose -f docker-compose.watchtower.yml up -d
```

## 보안 주의사항

1. **watchtower-config.json**은 절대 Git에 커밋하지 마세요
2. 파일 권한은 반드시 600으로 설정하세요
3. 프로덕션 환경에서는 더 안전한 비밀 관리 방법을 사용하세요

## 업데이트 주기

- **기본값**: 5분 (300초)
- **변경 방법**: `WATCHTOWER_POLL_INTERVAL` 환경 변수 수정
- **권장 설정**: 
  - 개발: 60초
  - 스테이징: 300초 (5분)
  - 프로덕션: 600초 (10분)

## CI/CD 플로우

1. 코드 푸시 → GitHub Actions 트리거
2. Docker 이미지 빌드 → registry.jclee.me 푸시
3. Watchtower가 새 이미지 감지 (5분 이내)
4. 자동으로 컨테이너 재시작
5. 헬스 체크로 정상 동작 확인

## 모니터링 대시보드

향후 Prometheus + Grafana 연동 예정:
- 컨테이너 메트릭
- 업데이트 이벤트
- 애플리케이션 성능
- Redis 캐시 히트율