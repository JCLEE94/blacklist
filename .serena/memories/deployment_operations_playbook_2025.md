# 배포 및 운영 플레이북 (2025년)

## GitOps 배포 프로세스

### 표준 배포 절차
```bash
# Phase 1: 사전 검증 (로컬)
make lint && make test              # 완전한 코드 품질 검사
docker build -t test-build .        # 로컬 빌드 테스트
docker run --rm test-build pytest   # 컨테이너 내 테스트

# Phase 2: 배포 실행
make deploy                         # 전체 GitOps 파이프라인
# 내부: docker-build → docker-push → argocd-sync

# Phase 3: 배포 검증  
kubectl get pods -n blacklist -w   # 파드 상태 실시간 모니터링
curl -f http://blacklist.jclee.me/health | jq  # 헬스체크

# Phase 4: 성능 검증
curl -w "Time: %{time_total}s\n" http://blacklist.jclee.me/api/blacklist/active
# 목표: <100ms 응답시간
```

### 배포 성공률 개선 전략 (60% → 95%)

#### 실패 원인 분석
1. **ArgoCD 동기화 실패** (40%) - path 설정 불일치
2. **리소스 제약** (25%) - 파드 스케줄링 실패
3. **헬스체크 실패** (20%) - 의존성 서비스 미준비
4. **이미지 빌드 실패** (15%) - 의존성 설치 오류

#### 해결 방법
```bash
# 1. ArgoCD 설정 최적화
argocd app set blacklist --path k8s/overlays/production
argocd app sync blacklist --timeout 600  # 10분 타임아웃

# 2. 리소스 사전 확인
kubectl top nodes                   # 노드 리소스 사용률
kubectl describe nodes | grep -A5 "Allocated resources"

# 3. 의존성 서비스 검증
kubectl get pods -n blacklist | grep -E "(redis|postgres)"
curl http://blacklist-redis:6379/ping

# 4. 빌드 최적화 (다단계 빌드)
FROM python:3.9-slim AS deps
# 의존성만 먼저 설치하여 캐시 활용
```

## 장애 대응 절차

### 우선순위별 대응 시간
- **P0 (서비스 중단)**: 15분 이내 복구
- **P1 (주요 기능 장애)**: 2시간 이내  
- **P2 (일부 기능 이상)**: 24시간 이내
- **P3 (개선 요청)**: 주간 계획

### P0 장애 대응 플레이북

#### 1. 서비스 접근 불가 (502/503/504)
```bash
# 즉시 확인
kubectl get pods -n blacklist          # 파드 상태
kubectl get svc -n blacklist           # 서비스 상태  
kubectl get ingress -n blacklist       # 인그레스 상태

# 로그 확인
kubectl logs -f deployment/blacklist -n blacklist --tail=100
kubectl describe pod <failing-pod> -n blacklist

# 긴급 롤백
kubectl rollout undo deployment/blacklist -n blacklist
kubectl rollout status deployment/blacklist -n blacklist
```

#### 2. 데이터 수집 실패 (컬렉션 시스템)
```bash
# 수집 상태 확인
curl http://blacklist.jclee.me/api/collection/status | jq

# 수동 트리거
curl -X POST http://blacklist.jclee.me/api/collection/regtech/trigger
curl -X POST http://blacklist.jclee.me/api/collection/secudium/trigger

# 로그 분석
kubectl logs deployment/blacklist -n blacklist | grep -i collection
```

#### 3. Redis 캐시 장애
```bash
# Redis 파드 상태 확인
kubectl get pods -n blacklist | grep redis
kubectl logs redis-deployment -n blacklist

# 애플리케이션은 자동으로 메모리 캐시로 폴백
# 필요시 Redis 재시작
kubectl delete pod redis-xxx -n blacklist  # 자동 재생성
```

### 성능 저하 대응

#### API 응답시간 증가 (>1초)
```bash
# 1. 현재 성능 측정
curl -w "@curl-format.txt" http://blacklist.jclee.me/api/blacklist/active

# 2. 리소스 사용률 확인  
kubectl top pods -n blacklist
kubectl describe hpa blacklist -n blacklist  # HPA 상태

# 3. 캐시 상태 점검
redis-cli -h blacklist-redis info memory
redis-cli -h blacklist-redis dbsize

# 4. 데이터베이스 상태
python3 -c "from src.core.container import get_container; 
c = get_container(); 
print(c.get('unified_service').get_system_health())"
```

#### 메모리 사용량 급증
```bash
# 파드 리소스 제한 확인
kubectl describe pod <pod-name> -n blacklist | grep -A10 Limits

# 메모리 프로파일링 활성화 (임시)
kubectl set env deployment/blacklist FLASK_PROFILING=true -n blacklist

# 캐시 정리
redis-cli -h blacklist-redis flushdb
```

## 모니터링 및 알림

### 핵심 메트릭 모니터링
```bash
# 헬스체크 (30초마다 자동)
*/30 * * * * curl -f http://blacklist.jclee.me/health || echo "Health check failed"

# 성능 벤치마크 (매시간)
0 * * * * python3 /path/to/performance_benchmark.py

# 리소스 사용률 (5분마다)  
*/5 * * * * kubectl top pods -n blacklist --no-headers | awk '{print $2, $3}'
```

### 알림 설정 (Slack/Email)
```yaml
# Prometheus AlertManager 규칙
groups:
- name: blacklist-alerts
  rules:
  - alert: BlacklistServiceDown
    expr: up{job="blacklist"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Blacklist service is down"
      
  - alert: HighResponseTime  
    expr: http_request_duration_seconds > 1.0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "API response time > 1s"
```

## 백업 및 복구

### 데이터베이스 백업 (일일)
```bash
# SQLite 백업 (개발환경)
cp /app/instance/blacklist.db /backup/blacklist_$(date +%Y%m%d).db

# PostgreSQL 백업 (프로덕션)  
kubectl exec postgres-pod -n blacklist -- pg_dump blacklist > backup_$(date +%Y%m%d).sql
```

### 설정 백업 (주간)
```bash
# Kubernetes 리소스 백업
kubectl get all -n blacklist -o yaml > k8s_backup_$(date +%Y%m%d).yaml

# ArgoCD 애플리케이션 백업
argocd app get blacklist -o yaml > argocd_app_backup.yaml
```

### 복구 절차
```bash
# 1. 데이터베이스 복구
kubectl cp backup.sql postgres-pod:/tmp/
kubectl exec postgres-pod -- psql blacklist < /tmp/backup.sql

# 2. 애플리케이션 복구 (이전 버전)
kubectl set image deployment/blacklist blacklist=registry.jclee.me/blacklist:previous

# 3. 설정 복구
kubectl apply -f k8s_backup.yaml
```

## 보안 운영

### 정기 보안 점검 (주간)
```bash
# 컨테이너 취약점 스캔
trivy image registry.jclee.me/blacklist:latest

# 의존성 보안 스캔  
safety check --json > security_report.json

# Kubernetes 보안 검사
kube-bench --targets node,policies,controlplane
```

### 로그 보안 감사 (일일)
```bash
# 실패한 인증 시도
kubectl logs deployment/blacklist -n blacklist | grep "Authentication failed"

# 비정상적 API 호출
kubectl logs deployment/blacklist -n blacklist | grep -E "(429|401|403)"

# 시스템 리소스 이상 사용
kubectl top pods -n blacklist | awk '$3 > 80 {print "High CPU:", $1, $3}'
```

## 성능 최적화 체크리스트

### 주기적 최적화 (월간)
1. **데이터베이스 인덱스 분석**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM blacklist WHERE ip_address = '192.168.1.1';
   ```

2. **캐시 히트율 측정**
   ```bash
   redis-cli info stats | grep keyspace_hits
   ```

3. **메모리 누수 검사**
   ```python
   import psutil
   process = psutil.Process()
   memory_trend = track_memory_usage()
   ```

4. **API 엔드포인트 성능 프로파일링**
   ```bash
   python3 -m cProfile -o profile.stats main.py
   ```

이 플레이북을 통해 안정적이고 효율적인 서비스 운영을 보장할 수 있습니다.