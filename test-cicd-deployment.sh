#!/bin/bash

echo "===== CI/CD 배포 프로세스 증명 ====="
echo ""
echo "1. GitHub Actions 워크플로우 확인"
echo "================================"
echo "워크플로우 파일 위치:"
ls -la .github/workflows/ | grep -E "(deploy|cicd)"
echo ""

echo "2. 현재 실행 중인 컨테이너 이미지"
echo "================================"
kubectl get pods -n blacklist -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}' | grep blacklist

echo ""
echo "3. ArgoCD 애플리케이션 상태"
echo "================================"
kubectl get application blacklist -n argocd -o json | jq '{
  name: .metadata.name,
  sync_status: .status.sync.status,
  health_status: .status.health.status,
  source: {
    repoURL: .spec.source.repoURL,
    chart: .spec.source.chart,
    targetRevision: .spec.source.targetRevision
  },
  last_sync: .status.operationState.finishedAt,
  image_updater: .metadata.annotations."argocd-image-updater.argoproj.io/image-list"
}'

echo ""
echo "4. Docker Registry 이미지 확인"
echo "================================"
# 최신 이미지 태그 확인 (간접적으로)
echo "현재 사용 중인 이미지:"
kubectl get deployment blacklist -n blacklist -o jsonpath='{.spec.template.spec.containers[0].image}'

echo ""
echo ""
echo "5. 최근 배포 이벤트"
echo "================================"
kubectl get events -n blacklist --sort-by='.lastTimestamp' | grep -E "(Pulled|Started|Created)" | tail -5

echo ""
echo "6. CI/CD 파이프라인 구성 요소"
echo "================================"
echo "✅ GitHub Actions: .github/workflows/simple-deploy.yaml"
echo "✅ Docker Registry: registry.jclee.me/jclee94/blacklist"
echo "✅ ArgoCD: https://charts.jclee.me (Helm Charts)"
echo "✅ Kubernetes: blacklist namespace"
echo "✅ Image Updater: 자동 이미지 감지 및 업데이트"

echo ""
echo "7. 배포 프로세스 흐름"
echo "================================"
echo "1) 코드 Push → GitHub main 브랜치"
echo "2) GitHub Actions 트리거 → Docker 빌드"
echo "3) Docker Push → registry.jclee.me"
echo "4) ArgoCD Image Updater → 새 이미지 감지"
echo "5) ArgoCD → Kubernetes 배포"
echo "6) Health Check → 서비스 확인"

echo ""
echo "8. 현재 서비스 상태"
echo "================================"
curl -s http://192.168.50.110:32542/health | jq '{status: .status, version: .details.version, timestamp: .timestamp}'

echo ""
echo "테스트 완료: $(date '+%Y-%m-%d %H:%M:%S')"