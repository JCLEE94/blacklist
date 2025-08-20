# Watchtower 자동 업데이트 시스템

## 개요
Watchtower는 Docker 컨테이너의 자동 업데이트를 관리하는 서비스로, registry.jclee.me에서 새로운 이미지 버전을 모니터링하고 자동으로 업데이트를 수행합니다.

## 설정 방법

### docker-compose.watchtower.yml
```yaml
version: '3.8'
services:
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_POLL_INTERVAL=300  # 5분마다 체크
      - WATCHTOWER_INCLUDE_RESTARTING=true
      - WATCHTOWER_INCLUDE_STOPPED=true
    command: --label-enable --cleanup
    restart: unless-stopped
    networks:
      - blacklist_default

networks:
  blacklist_default:
    external: true
```

### 기본 서비스에 라벨 추가
```yaml
# docker-compose.yml에 추가
services:
  blacklist:
    image: registry.jclee.me/blacklist:latest
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    # ... 기존 설정
```

## 작동 원리
1. **모니터링**: 5분마다 registry.jclee.me/blacklist:latest 체크
2. **업데이트 감지**: 새로운 이미지 SHA 발견 시
3. **자동 업데이트**: 
   - 새 이미지 pull
   - 기존 컨테이너 중지
   - 새 컨테이너 시작
   - 이전 이미지 정리

## 배포 파이프라인과 연동
```
GitHub Push → Actions Build → Registry Push → Watchtower Detection → Auto Update
```

## 관리 명령어
```bash
# Watchtower 시작
docker-compose -f docker-compose.watchtower.yml up -d

# Watchtower 상태 확인
docker logs watchtower

# 수동 업데이트 강제 실행
docker exec watchtower /watchtower --run-once

# Watchtower 중지
docker-compose -f docker-compose.watchtower.yml down
```

## 장점
- **완전 자동화**: 수동 개입 없이 지속적 배포
- **즉시 업데이트**: GitHub Actions 완료 후 5분 내 자동 배포
- **롤백 안전성**: 실패 시 이전 버전 유지
- **리소스 정리**: 이전 이미지 자동 삭제

## 주의사항
- 프로덕션에서는 업무 시간 외 업데이트 권장
- 중요 업데이트 전 수동 테스트 필요
- 로그 모니터링으로 업데이트 상태 확인

## 모니터링
```bash
# 업데이트 로그 확인
docker logs -f watchtower

# 서비스 상태 확인  
docker-compose ps
curl http://localhost:32542/health
```