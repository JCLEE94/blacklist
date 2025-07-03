# 자동 배포 실패 재발 방지 가이드

## 🚨 주요 실패 원인 및 해결책

### 1. Docker Registry 인증 실패 (401 Unauthorized)

**원인:**
- GitHub Secrets에 잘못된 인증 정보 저장
- Secret 이름 불일치 (DOCKER_USERNAME vs REGISTRY_USERNAME)
- 토큰 만료 또는 권한 부족

**해결책:**
```bash
# GitHub Secrets 설정 확인
gh secret list

# 필수 Secrets 설정
gh secret set DOCKER_USERNAME -b "qws9411"
gh secret set DOCKER_PASSWORD -b "bingogo1"
gh secret set REGISTRY_USERNAME -b "qws9411"
gh secret set REGISTRY_PASSWORD -b "bingogo1"
```

### 2. PVC/PV 바인딩 실패

**원인:**
- PV가 이전 PVC에 바인딩된 상태 (Released)
- StorageClass 불일치
- 용량 요구사항 불일치

**해결책:**
```bash
# PV 상태 확인
kubectl get pv | grep blacklist

# Released 상태의 PV 수정
kubectl patch pv blacklist-data-pv -p '{"spec":{"claimRef": null}}'
kubectl patch pv blacklist-instance-pv -p '{"spec":{"claimRef": null}}'
kubectl patch pv blacklist-logs-pv -p '{"spec":{"claimRef": null}}'

# PVC 재생성
kubectl delete pvc --all -n blacklist
kubectl apply -k k8s/
```

### 3. Auto-updater CronJob 누락

**원인:**
- CronJob 정의 파일 미적용
- RBAC 권한 부족
- ServiceAccount 누락

**해결책:**
```bash
# Enhanced auto-updater 적용
kubectl apply -f k8s/auto-updater-enhanced.yaml

# 상태 확인
kubectl get cronjob -n blacklist
kubectl get jobs -n blacklist | grep auto-updater
```

## 🛡️ 시스템적 재발 방지 대책

### 1. 배포 전 사전 검증

**수동 검증 단계:**
- Docker Registry 인증 확인
- GitHub Secrets 검증
- Kubernetes 연결성 확인
- PV/PVC 상태 체크

### 2. 자동 복구 스크립트

**`scripts/recovery/blacklist-recovery.sh` 기능:**
```bash
#!/bin/bash
# 1. PVC 문제 자동 해결
# 2. Kubernetes 매니페스트 재적용
# 3. 강제 이미지 업데이트
# 4. 헬스 체크 검증
```

### 3. CI/CD 파이프라인 개선

**강화된 검증 단계:**
- Registry 로그인 실패 시 즉시 중단
- 다중 태그 전략 (SHA-7, SHA-8, timestamp)
- 롤아웃 상태 확인 (최대 10분 대기)
- 실패 시 자동 롤백

### 4. Enhanced Auto-updater

**개선사항:**
- ServiceAccount 및 RBAC 설정
- 5분마다 자동 실행
- 롤아웃 실패 시 자동 롤백
- Post-update 헬스 체크

## 📋 체크리스트

### 배포 전 확인사항

- [ ] GitHub Secrets 모두 설정됨
- [ ] Docker Registry 로그인 가능
- [ ] Kubernetes 클러스터 접근 가능
- [ ] PV/PVC 상태 정상
- [ ] Auto-updater CronJob 실행 중

### 배포 후 확인사항

- [ ] 모든 Pod Running 상태
- [ ] Health endpoint 응답 정상
- [ ] 주요 API 엔드포인트 동작
- [ ] 로그에 에러 없음

## 🚀 Quick Setup

전체 시스템 설정을 자동화하는 스크립트 실행:

```bash
# 자동 배포 수정 설정 실행
./scripts/setup/auto-deployment-fix.sh

# 환경 변수 설정 (최초 1회)
cp .env.example .env
# .env 파일 편집하여 인증 정보 입력

# GitHub Actions 워크플로우 확인
ls -la .github/workflows/

# 수동 복구 (필요시)
./scripts/recovery/blacklist-recovery.sh
```

## 📊 모니터링

### GitHub Actions 대시보드
- Workflow runs: https://github.com/JCLEE94/blacklist/actions
- CI/CD Pipeline: "Enhanced Kubernetes CI/CD Pipeline" workflow

### Kubernetes 모니터링
```bash
# 실시간 Pod 상태
kubectl get pods -n blacklist -w

# Auto-updater 로그
kubectl logs -n blacklist -l app=auto-updater --tail=50 -f

# 최근 이벤트
kubectl get events -n blacklist --sort-by='.lastTimestamp'
```

## 🔔 알림 설정

Webhook URL 설정으로 배포 실패 시 즉시 알림:

```bash
# GitHub Secret 설정
gh secret set ALERT_WEBHOOK_URL -b "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
gh secret set DEPLOYMENT_WEBHOOK_URL -b "https://your-webhook-endpoint.com"
```

## 📝 트러블슈팅

### "Deployment not ready" 에러
```bash
# Pod 상태 확인
kubectl describe pods -n blacklist -l app=blacklist

# 최근 로그 확인
kubectl logs deployment/blacklist -n blacklist --tail=100

# PVC 상태 확인
kubectl get pvc -n blacklist
```

### "Registry authentication failed" 에러
```bash
# Secret 재생성
kubectl delete secret regcred -n blacklist
kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=$REGISTRY_USERNAME \
  --docker-password=$REGISTRY_PASSWORD \
  -n blacklist
```

### "Image pull backoff" 에러
```bash
# Registry 연결 테스트
docker login registry.jclee.me -u $REGISTRY_USERNAME -p $REGISTRY_PASSWORD

# 이미지 수동 pull 테스트
docker pull registry.jclee.me/blacklist:latest
```

---

이 가이드를 따라 설정하면 자동 배포 실패를 시스템적으로 방지하고, 
문제 발생 시 자동으로 복구할 수 있습니다.