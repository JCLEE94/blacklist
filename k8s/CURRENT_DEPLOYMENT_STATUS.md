# Blacklist 현재 배포 상태

## 배포 정보
- **배포 방식**: Helm Chart (ArgoCD 관리)
- **Chart Repository**: https://charts.jclee.me
- **Container Image**: registry.jclee.me/blacklist:latest
- **Namespace**: blacklist

## 실행 중인 리소스

### Pods
- `blacklist-6f5cd4f86b-6pntf` - 애플리케이션 (Running)
- `blacklist-redis-master-0` - Redis 캐시 (Running)

### Services
- `blacklist` - ClusterIP (8541)
- `blacklist-nodeport` - NodePort (8541:32542)
- `blacklist-redis-*` - Redis 서비스들

### ArgoCD
- Application: `blacklist`
- Status: Synced & Healthy
- Auto-sync: Enabled

## 접속 정보
- **내부 접속**: http://blacklist.blacklist.svc.cluster.local:8541
- **NodePort 접속**: http://192.168.50.110:32542
- **외부 도메인**: https://blacklist.jclee.me (→ 192.168.50.110:32542)

## Health Check
```bash
curl http://192.168.50.110:32542/health
```

## 관리 명령어

### ArgoCD 동기화
```bash
argocd app sync blacklist --grpc-web
```

### 로그 확인
```bash
kubectl logs -f deployment/blacklist -n blacklist
```

### 재시작
```bash
kubectl rollout restart deployment/blacklist -n blacklist
```

### 스케일 조정
```bash
kubectl scale deployment blacklist --replicas=3 -n blacklist
```