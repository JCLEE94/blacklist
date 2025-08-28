# MSA 아키텍처 가이드

## 🏗️ 아키텍처 개요

Blacklist Management System의 마이크로서비스 아키텍처(MSA) 전환이 완료되었습니다.

### 서비스 구성

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (8080)                      │
│  • 라우팅 • 인증 • 부하분산 • 캐싱 • 모니터링               │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
┌─────────▼─────┐ ┌───▼──────┐ ┌──▼─────────┐
│ Collection    │ │Blacklist │ │ Analytics  │
│ Service       │ │Management│ │ Service    │
│ (8000)        │ │ Service  │ │ (8002)     │
│               │ │ (8001)   │ │            │
│• REGTECH 수집 │ │• IP 관리 │ │• 트렌드 분석│
│• SECUDIUM 수집│ │• 검증     │ │• 통계 생성 │
│• 스케줄링     │ │• FortiGate│ │• 리포팅    │
└───────────────┘ └──────────┘ └────────────┘
         │             │              │
         └─────────────┼──────────────┘
                       │
              ┌────────▼────────┐
              │   PostgreSQL    │
              │     Redis       │
              │   (데이터 저장)  │
              └─────────────────┘
```

## 🔧 서비스별 역할

### 1. Collection Service (포트 8000)
- **역할**: 외부 소스에서 IP 데이터를 수집
- **기술스택**: FastAPI, asyncio, httpx
- **주요기능**:
  - REGTECH 데이터 수집 (인증 기반)
  - SECUDIUM 데이터 수집 (Excel 다운로드)
  - 스케줄링 및 배치 수집
  - 데이터 검증 및 정제

### 2. Blacklist Management Service (포트 8001)
- **역할**: IP 블랙리스트의 저장, 관리, 조회
- **기술스택**: FastAPI, SQLAlchemy, PostgreSQL
- **주요기능**:
  - IP 주소 CRUD 작업
  - 중복 제거 및 유효성 검사
  - FortiGate External Connector 형식 변환
  - 대량 데이터 처리 (배치 삽입/조회)

### 3. Analytics Service (포트 8002)
- **역할**: 데이터 분석, 통계 생성, 트렌드 분석
- **기술스택**: FastAPI, pandas, numpy
- **주요기능**:
  - 실시간 통계 생성
  - 트렌드 분석 (일별/주별/월별)
  - 지리적 분포 분석
  - 위협 유형별 분석

### 4. API Gateway (포트 8080)
- **역할**: 모든 외부 요청의 진입점
- **기술스택**: FastAPI, httpx
- **주요기능**:
  - 요청 라우팅
  - 인증 및 권한 관리
  - 레이트 리미팅
  - 캐싱 및 응답 최적화
  - 헬스체크 및 모니터링

## 🔄 데이터 흐름

### 1. 데이터 수집 흐름
```
External Sources → Collection Service → Blacklist Service → Database
     ↓
Analytics Service ← Database
```

### 2. API 요청 흐름
```
Client → API Gateway → Target Service → Database
   ↑                        ↓
   └── Response ←── Cache ←──┘
```

## 📊 분산 데이터 일관성 전략

### 1. 데이터베이스 일관성
- **단일 PostgreSQL 인스턴스**: 현재는 단일 DB로 ACID 속성 보장
- **읽기 복제본**: 분석 서비스용 읽기 전용 복제본 (향후 확장)
- **트랜잭션 관리**: 각 서비스에서 트랜잭션 범위 관리

### 2. 캐시 일관성
- **Redis 캐시**: 서비스별 캐시 네임스페이스 분리
- **TTL 기반 만료**: 데이터 특성에 따른 차등 TTL 적용
- **캐시 무효화**: 데이터 변경 시 관련 캐시 자동 무효화

### 3. 이벤트 기반 일관성 (향후 확장)
- **Message Queue**: RabbitMQ를 통한 이벤트 전파
- **Event Sourcing**: 중요한 도메인 이벤트의 추적 및 재생
- **CQRS 패턴**: 명령과 조회의 분리

## 🚀 배포 및 운영

### Docker Compose 배포
```bash
# 환경 변수 설정
source scripts/load-env.sh

# MSA 배포
./scripts/msa-deployment.sh deploy-docker

# 상태 확인
./scripts/msa-deployment.sh status

# 서비스 테스트
./scripts/msa-deployment.sh test
```

### Kubernetes 배포
```bash
# 환경 변수 설정
source scripts/load-env.sh

# MSA 배포
./scripts/msa-deployment.sh deploy-k8s

# 상태 확인
kubectl get pods -n blacklist-msa

# 포트포워딩으로 접속
kubectl port-forward service/api-gateway 8080:8080 -n blacklist-msa
```

## 📈 모니터링 및 관찰성

### 헬스체크 엔드포인트
- **API Gateway**: `GET /health`
- **각 서비스**: `GET /health`
- **통합 상태**: API Gateway에서 모든 서비스 상태 통합 표시

### 메트릭 수집
- **응답 시간**: 각 서비스별 응답 시간 측정
- **처리량**: RPS (Requests Per Second) 모니터링
- **에러율**: 4xx, 5xx 에러 비율 추적
- **리소스 사용량**: CPU, 메모리, 네트워크 사용량

### 로그 관리
- **구조화된 로깅**: JSON 형태의 로그 출력
- **상관관계 ID**: 요청 추적을 위한 고유 ID
- **로그 레벨**: DEBUG, INFO, WARNING, ERROR

## 🔒 보안 고려사항

### 네트워크 보안
- **서비스 간 통신**: 내부 네트워크로 제한
- **API Gateway**: 유일한 외부 노출 포인트
- **TLS 암호화**: 외부 통신은 HTTPS 강제

### 인증 및 권한
- **JWT 토큰**: stateless 인증
- **역할 기반 접근제어**: admin, user, anonymous
- **API 키**: 시스템 간 통신용

### 데이터 보안
- **민감 정보 암호화**: 환경 변수로 관리
- **SQL 인젝션 방지**: ORM 사용
- **입력 검증**: 모든 입력 데이터 검증

## 🔧 개발 가이드

### 새 서비스 추가
1. `services/new-service/` 디렉토리 생성
2. FastAPI 애플리케이션 작성
3. Dockerfile 및 requirements.txt 작성
4. API Gateway에 라우팅 규칙 추가
5. Docker Compose 및 Kubernetes 매니페스트 업데이트

### 로컬 개발
```bash
# 개별 서비스 실행
cd services/collection-service
python app.py

# 전체 스택 실행
docker-compose -f docker-compose.msa.yml up -d

# 개발용 핫리로드
docker-compose -f docker-compose.msa.yml up --build
```

### 테스트
```bash
# API 문서 확인
curl http://localhost:8080/docs

# 헬스체크
curl http://localhost:8080/health

# 블랙리스트 조회
curl http://localhost:8080/api/v1/blacklist/active

# 분석 리포트
curl http://localhost:8080/api/v1/analytics/report
```

## 🎯 성능 최적화

### 캐싱 전략
- **API Gateway**: 자주 요청되는 데이터 캐싱
- **Database Query**: 복잡한 분석 쿼리 결과 캐싱
- **Static Data**: 변경 빈도가 낮은 데이터 장기 캐싱

### 데이터베이스 최적화
- **인덱스**: IP 주소, 날짜 기반 인덱스
- **파티셔닝**: 날짜별 테이블 파티셔닝
- **읽기 복제본**: 분석 쿼리용 별도 인스턴스

### 스케일링 방안
- **수평 확장**: 서비스별 독립적인 스케일링
- **로드 밸런싱**: API Gateway에서 라운드로빈
- **Auto Scaling**: Kubernetes HPA 활용

## 🚨 장애 대응

### Circuit Breaker
- **서비스 간 호출**: 장애 전파 방지
- **외부 API 호출**: 타임아웃 및 재시도 로직
- **데이터베이스**: 연결 풀 관리

### 백업 및 복구
- **데이터베이스 백업**: 일일 자동 백업
- **설정 백업**: ConfigMap, Secret 백업
- **재해 복구**: 다중 가용영역 배포

### 모니터링 알림
- **서비스 다운**: 즉시 알림
- **응답 시간 증가**: 임계값 초과 시 알림
- **에러율 증가**: 5% 초과 시 알림

## 📋 마이그레이션 가이드

### 기존 모놀리식에서 MSA로 전환

1. **점진적 전환**:
   - API Gateway를 프록시로 설정
   - 기능별로 순차적 마이그레이션
   - 트래픽 점진적 전환

2. **데이터 마이그레이션**:
   - 기존 SQLite 데이터를 PostgreSQL로 이관
   - 데이터 무결성 검증
   - 백업 후 전환

3. **설정 마이그레이션**:
   - 환경 변수를 ConfigMap/Secret으로 변환
   - 로깅 설정 업데이트
   - 모니터링 설정 추가

## 🔮 향후 확장 계획

### 1. Service Mesh 도입
- **Istio**: 트래픽 관리, 보안, 관찰성
- **mTLS**: 서비스 간 암호화 통신
- **분산 추적**: Jaeger 통합

### 2. 이벤트 기반 아키텍처
- **Event Sourcing**: 도메인 이벤트 저장
- **CQRS**: 명령과 조회 분리
- **Saga Pattern**: 분산 트랜잭션 관리

### 3. 고급 분석 기능
- **ML Pipeline**: 머신러닝 기반 위협 탐지
- **Real-time Processing**: Kafka + Spark
- **Predictive Analytics**: 예측 분석 서비스

이 MSA 아키텍처는 확장성, 유지보수성, 장애 격리를 통해 더 안정적이고 효율적인 시스템을 제공합니다.