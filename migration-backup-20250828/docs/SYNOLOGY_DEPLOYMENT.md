# Synology NAS 자동 배포 가이드

## 📋 개요
Synology NAS (192.168.50.215:1111)에 Blacklist Management System을 자동 배포하는 방법

## 🏗️ 디렉토리 구조

```
/volume1/docker/blacklist/
├── config/              # 설정 파일
│   └── .env            # 환경 변수
├── data/               # 애플리케이션 데이터
│   ├── blacklist_entries/
│   ├── exports/
│   └── collection_logs/
├── logs/               # 로그 파일
├── scripts/            # 자동화 스크립트
│   ├── update.sh      # 업데이트 스크립트
│   ├── monitor.sh     # 모니터링 스크립트
│   └── backup.sh      # 백업 스크립트
├── backup/             # 백업 파일
└── docker-compose.yml  # Docker Compose 설정
```

## 🚀 초기 설정

### 1. SSH 접속
```bash
ssh -p 1111 qws941@192.168.50.215
# 비밀번호: bingogo1
```

### 2. 배포 스크립트 실행
```bash
# 로컬에서 실행
./scripts/synology-deploy.sh
```

### 3. 환경 변수 설정
```bash
# NAS에서 실행
cd /volume1/docker/blacklist
nano config/.env

# 다음 값들을 실제 값으로 수정:
REGTECH_USERNAME=실제_사용자명
REGTECH_PASSWORD=실제_비밀번호
SECUDIUM_USERNAME=실제_사용자명
SECUDIUM_PASSWORD=실제_비밀번호
SECRET_KEY=복잡한_시크릿_키
JWT_SECRET_KEY=복잡한_JWT_키
```

### 4. 서비스 시작
```bash
cd /volume1/docker/blacklist
docker-compose up -d
```

## 🔄 자동 배포 방법

### 방법 1: Synology Task Scheduler
DSM 제어판 > 작업 스케줄러에서 다음 작업 추가:

1. **자동 업데이트 작업**
   - 스케줄: 매일 오전 2시
   - 명령: `/volume1/docker/blacklist/scripts/update.sh`

2. **헬스 모니터링 작업**
   - 스케줄: 5분마다
   - 명령: `/volume1/docker/blacklist/scripts/monitor.sh`

3. **백업 작업**
   - 스케줄: 매일 오전 3시
   - 명령: `/volume1/docker/blacklist/scripts/backup.sh`

### 방법 2: GitHub Webhook
1. Webhook 서버 실행 (별도 서버 필요)
```bash
export WEBHOOK_SECRET=your-webhook-secret
export DEPLOY_API_KEY=your-api-key
python3 scripts/synology-webhook.py
```

2. GitHub 저장소 설정
   - Settings > Webhooks > Add webhook
   - Payload URL: `http://your-server:8080/webhook`
   - Content type: `application/json`
   - Secret: 위에서 설정한 WEBHOOK_SECRET

### 방법 3: 수동 배포
```bash
# 로컬에서 실행
ssh -p 1111 qws941@192.168.50.215 'cd /volume1/docker/blacklist && docker-compose pull && docker-compose down && docker-compose up -d'
```

## 📊 모니터링

### 서비스 상태 확인
```bash
ssh -p 1111 qws941@192.168.50.215 'cd /volume1/docker/blacklist && docker-compose ps'
```

### 로그 확인
```bash
# 실시간 로그
ssh -p 1111 qws941@192.168.50.215 'cd /volume1/docker/blacklist && docker-compose logs -f'

# 배포 로그
ssh -p 1111 qws941@192.168.50.215 'tail -f /volume1/docker/blacklist/logs/deployment.log'

# 헬스체크 로그
ssh -p 1111 qws941@192.168.50.215 'tail -f /volume1/docker/blacklist/logs/health.log'
```

### API 헬스체크
```bash
curl http://192.168.50.215:32542/api/collection/status
```

## 🔧 문제 해결

### 서비스 재시작
```bash
ssh -p 1111 qws941@192.168.50.215 'cd /volume1/docker/blacklist && docker-compose restart'
```

### 전체 재배포
```bash
ssh -p 1111 qws941@192.168.50.215 'cd /volume1/docker/blacklist && docker-compose down && docker-compose pull && docker-compose up -d'
```

### 백업 복원
```bash
ssh -p 1111 qws941@192.168.50.215
cd /volume1/docker/blacklist
# 최신 백업 파일 찾기
LATEST_BACKUP=$(ls -t backup/blacklist_backup_*.tar.gz | head -1)
# 복원
tar -xzf $LATEST_BACKUP
docker-compose restart
```

## 🔐 보안 설정

### SSH 키 설정 (권장)
```bash
# 로컬에서 SSH 키 생성
ssh-keygen -t rsa -b 4096 -f ~/.ssh/synology_nas

# 공개 키 복사
ssh-copy-id -p 1111 -i ~/.ssh/synology_nas.pub qws941@192.168.50.215

# SSH 설정 파일 수정
cat >> ~/.ssh/config << EOF
Host synology-nas
    HostName 192.168.50.215
    Port 1111
    User qws941
    IdentityFile ~/.ssh/synology_nas
EOF

# 이제 간단하게 접속
ssh synology-nas
```

### 방화벽 설정
DSM 제어판 > 보안 > 방화벽에서:
- 포트 32542 (Blacklist 웹 서비스) 허용
- 포트 1111 (SSH) 특정 IP만 허용

## 📚 유용한 명령어

```bash
# 빠른 배포
alias deploy-nas='ssh synology-nas "cd /volume1/docker/blacklist && docker-compose pull && docker-compose down && docker-compose up -d"'

# 로그 보기
alias nas-logs='ssh synology-nas "cd /volume1/docker/blacklist && docker-compose logs -f"'

# 상태 확인
alias nas-status='ssh synology-nas "cd /volume1/docker/blacklist && docker-compose ps"'
```

## 🆘 지원
문제 발생 시:
1. 로그 파일 확인 (`/volume1/docker/blacklist/logs/`)
2. Docker 컨테이너 상태 확인
3. 네트워크 연결 상태 확인
4. GitHub Issues에 문제 보고