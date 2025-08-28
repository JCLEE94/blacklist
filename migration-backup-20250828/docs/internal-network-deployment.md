# 사내 내부망 배포 가이드

## 배포 옵션

### 옵션 1: Docker Compose 단독 실행 (추천) ⭐
**장점**: 가장 간단, 의존성 최소, 운영 쉬움
**단점**: 확장성 제한

### 옵션 2: K3s 경량 쿠버네티스
**장점**: 오케스트레이션, 자동 복구
**단점**: 복잡도 증가

### 옵션 3: Systemd 서비스
**장점**: OS 레벨 관리, Docker 불필요
**단점**: Python 환경 직접 관리

## 옵션 1 상세: Docker Compose 배포 (추천)

### 1. 오프라인 이미지 준비
```bash
# 개발 환경에서 이미지 저장
docker save -o blacklist-images.tar \
  registry.jclee.me/blacklist:latest \
  redis:7-alpine

# 파일 크기: 약 150-200MB
```

### 2. 배포 패키지 구성
```
blacklist-deployment/
├── blacklist-images.tar       # Docker 이미지
├── docker-compose.prod.yml    # 프로덕션 설정
├── .env.production            # 환경 변수
├── install.sh                 # 설치 스크립트
├── data/                      # 초기 데이터
└── scripts/                   # 운영 스크립트
```

### 3. 사내망 설치 과정
```bash
# 1. 이미지 로드
docker load -i blacklist-images.tar

# 2. 서비스 시작
docker-compose -f docker-compose.prod.yml up -d

# 3. 접속
http://내부IP:32542
```

## 배포 파일 생성