# Blacklist 배포 가이드

## 프로덕션 서버 배포

### 1. 서버 정보
- **서버**: `docker@192.168.50.215:1111`
- **레지스트리**: `registry.jclee.me`
- **애플리케이션 포트**: `2541`

### 2. 배포 디렉토리 구조
```
/var/services/homes/docker/app/blacklist/
├── instance/          # SQLite 데이터베이스
├── data/              # 애플리케이션 데이터
├── logs/              # 애플리케이션 로그
└── docker-compose.yml # 배포 설정
```

### 3. 초기 배포
```bash
# 1. SSH 접속
ssh -p 1111 docker@192.168.50.215

# 2. 디렉토리 생성
mkdir -p /var/services/homes/docker/app/blacklist/{instance,data,logs}
cd /var/services/homes/docker/app/blacklist

# 3. docker-compose.yml 복사
# docker-compose.prod.yml 내용을 docker-compose.yml로 저장

# 4. 컨테이너 시작
/usr/local/bin/docker-compose up -d
```

### 4. Watchtower 자동 업데이트
- Watchtower가 30초마다 새 이미지를 확인
- `registry.jclee.me/blacklist:latest` 태그 감시
- 새 이미지 발견 시 자동으로 재배포

### 5. 데이터 영속성
볼륨 마운트를 통해 다음 데이터가 보존됩니다:
- `/app/instance` → 데이터베이스 (blacklist.db)
- `/app/data` → 애플리케이션 데이터
- `/app/logs` → 로그 파일

### 6. 모니터링
```bash
# 컨테이너 상태 확인
/usr/local/bin/docker ps | grep blacklist

# 로그 확인
/usr/local/bin/docker logs -f blacklist-app

# 헬스체크
curl http://localhost:2541/health
```

### 7. 수동 업데이트
```bash
# 최신 이미지 가져오기
/usr/local/bin/docker pull registry.jclee.me/blacklist:latest

# 재시작
/usr/local/bin/docker-compose restart blacklist-app
```

## CI/CD 파이프라인

1. **코드 푸시** → GitHub main 브랜치
2. **GitHub Actions** → 테스트 및 빌드
3. **이미지 푸시** → registry.jclee.me
4. **Watchtower** → 자동 감지 및 배포
5. **검증** → 헬스체크 및 smoke 테스트