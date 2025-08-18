# Docker Compose 기반 배포 가이드

## 🐳 K8s에서 Compose로 완전 전환 완료

### 배포 전략 변경
- ❌ **이전**: Kubernetes + ArgoCD + Helm
- ✅ **현재**: Docker Compose + Watchtower + Registry

### 배포 환경

#### 개발 환경
```bash
# 기본 개발 서버
docker-compose -f docker/docker-compose.yml up -d

# 로컬 개발 (포트 32542)
docker-compose up -d
```

#### 프로덕션 환경
```bash
# 프로덕션 설정으로 배포
docker-compose -f deployment/docker-compose.production.yml up -d

# 모니터링 포함 배포
docker-compose -f deployment/docker-compose.production.yml --profile monitoring up -d
```

### 자동 배포 플로우

#### 1. GitHub Actions (자동)
```
코드 Push → GitHub Actions → Docker Build → Registry Push → 
Watchtower 감지 (1-2시간) → 자동 Pull & 재시작
```

#### 2. 즉시 수동 배포
```bash
# 최신 이미지로 업데이트
docker-compose pull && docker-compose up -d

# 특정 서비스만 업데이트
docker-compose up -d --no-deps blacklist
```

### 서비스 구성

| 서비스 | 포트 | 용도 | 리소스 |
|--------|------|------|---------|
| blacklist | 32542 | 메인 애플리케이션 | 1GB RAM, 1 CPU |
| redis | 6379 | 캐시 | 512MB RAM |
| watchtower | - | 자동 업데이트 | 256MB RAM |
| prometheus | 9090 | 모니터링 (선택) | 512MB RAM |

### 상태 확인

```bash
# 서비스 상태
docker-compose ps

# 헬스체크
curl http://localhost:32542/health

# 로그 확인
docker-compose logs -f blacklist

# 리소스 사용량
docker stats
```

### 백업 및 복구

#### 데이터 백업
```bash
# Redis 데이터 백업
docker exec blacklist-redis-prod redis-cli BGSAVE
cp -r redis-data-prod redis-backup-$(date +%Y%m%d)

# 애플리케이션 데이터 백업
tar -czf data-backup-$(date +%Y%m%d).tar.gz data/
```

#### 복구
```bash
# 서비스 중단
docker-compose down

# 데이터 복구
tar -xzf data-backup-YYYYMMDD.tar.gz

# 서비스 재시작
docker-compose up -d
```

### 트러블슈팅

#### 일반적인 문제
1. **포트 충돌**: `netstat -tlnp | grep 32542`로 확인
2. **디스크 공간**: `docker system prune -f`로 정리
3. **메모리 부족**: `docker stats`로 리소스 모니터링

#### 긴급 복구
```bash
# 모든 컨테이너 재시작
docker-compose restart

# 강제 이미지 업데이트
docker-compose pull --ignore-pull-failures
docker-compose up -d --force-recreate

# 네트워크 재생성
docker-compose down
docker network prune -f
docker-compose up -d
```

### 성능 최적화

#### 프로덕션 설정
- **Gunicorn**: 4 workers, 2 threads
- **Redis**: 512MB 메모리 제한, LRU 정책
- **로그**: JSON 형식, 50MB 로테이션

#### 모니터링
- **Prometheus**: 메트릭 수집 (포트 9090)
- **Health checks**: 30초 간격 자동 체크
- **Watchtower**: 2시간 간격 업데이트 체크

### 보안 고려사항

#### 네트워크 보안
- **Internal network**: 172.25.0.0/16 (프로덕션)
- **포트 노출**: 32542만 외부 접근
- **컨테이너 격리**: 각 서비스별 분리

#### 데이터 보안
- **환경 변수**: .env 파일로 관리
- **시크릿**: Docker secrets 또는 외부 키 관리
- **백업 암호화**: 민감 데이터 암호화 저장

## 마이그레이션 완료 체크리스트

- [x] K8s 매니페스트 아카이브 처리 (archive/k8s-deprecated-20250818/)
- [x] Docker Compose 프로덕션 설정 생성
- [x] Watchtower 자동 업데이트 구성
- [x] GitHub Actions 워크플로우 업데이트
- [x] 배포 가이드 문서화
- [x] 모니터링 및 로깅 설정
- [x] 프로젝트 구조 정리 및 파일 조직화 (2025-08-18)
- [x] Root 디렉토리 위반 파일 정리 완료
- [x] 설정 파일 통합 관리 (config/ 디렉토리)

## 최종 프로젝트 구조 (정리 완료)

```
blacklist/
├── archive/                    # K8s 아카이브 (deprecated-20250818)
├── config/                     # 모든 설정 파일 통합
│   ├── .env.* (환경별 설정)
│   ├── docker-compose.prod.yml
│   └── production-config.yml
├── deployment/                 # Docker Compose 배포 파일
│   ├── README.md (이 파일)
│   └── docker-compose.production.yml
├── docker/                     # 개발용 Docker 설정
├── docs/                      # 문서화
├── scripts/                   # 스크립트 통합
└── src/                       # 소스 코드
```

🎯 **K8s 복잡성 제거하고 Compose 기반 간단한 배포 체계 완성!**
✅ **프로젝트 구조 정리 완료 - 깔끔한 디렉토리 조직화**