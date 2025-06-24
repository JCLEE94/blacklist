# Watchtower 분리 운영 가이드

## 1. Watchtower 전용 실행 (전체 시스템용)

```bash
# Watchtower 설정 디렉토리로 이동
cd /opt/watchtower

# watchtower-config.json 생성
cat > watchtower-config.json << 'EOF'
{
  "auths": {
    "registry.jclee.me": {
      "auth": "cXdzOTQxOmJpbmdvZ28xbDch"
    }
  }
}
EOF

# 권한 설정
chmod 600 watchtower-config.json

# docker-compose 파일 다운로드
curl -o docker-compose.yml https://raw.githubusercontent.com/qws941/blacklist-management/main/deployment/docker-compose.watchtower-only.yml

# Watchtower 시작
docker-compose up -d
```

## 2. Blacklist 앱 전용 실행

```bash
# Blacklist 디렉토리로 이동
cd /var/services/homes/docker/app/blacklist

# docker-compose 파일 다운로드
curl -o docker-compose.yml https://raw.githubusercontent.com/qws941/blacklist-management/main/deployment/docker-compose.blacklist-only.yml

# 필요한 디렉토리 생성
mkdir -p instance logs data

# Blacklist 서비스 시작
docker-compose up -d
```

## 장점

1. **Watchtower 중앙 관리**
   - 한 곳에서 모든 registry.jclee.me 이미지 관리
   - 여러 서비스 동시 모니터링

2. **독립적 운영**
   - 각 서비스는 자체 docker-compose로 관리
   - Watchtower 재시작이 서비스에 영향 없음

3. **유연한 배포**
   - 서비스별로 다른 디렉토리에 배포 가능
   - 개별 서비스 관리 용이

## 운영 명령어

### Watchtower 관리
```bash
cd /opt/watchtower
docker-compose logs -f           # 로그 확인
docker-compose restart           # 재시작
docker-compose down              # 중지
```

### Blacklist 관리
```bash
cd /var/services/homes/docker/app/blacklist
docker-compose logs -f           # 로그 확인
docker-compose restart           # 재시작
docker-compose down              # 중지
docker-compose pull && docker-compose up -d  # 수동 업데이트
```

## 주의사항

- Watchtower는 시스템당 하나만 실행
- watchtower-config.json은 보안상 중요하므로 권한 관리 필수
- 모든 registry.jclee.me 이미지가 자동 업데이트됨