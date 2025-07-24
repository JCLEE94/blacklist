#!/bin/bash
# GitOps 완전 자동화 설정 스크립트

echo "🚀 GitOps 완전 자동화 설정 시작..."

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 설정
ARGOCD_SERVER="${ARGOCD_SERVER:-argocd.local}"
ARGOCD_PASSWORD="${ARGOCD_PASSWORD:-admin}"
GITHUB_REPO="JCLEE94/blacklist"
REGISTRY="registry.jclee.me"

# 1. ArgoCD CLI 설치 확인
echo -e "${BLUE}1. ArgoCD CLI 설치 확인${NC}"
if ! command -v argocd &> /dev/null; then
    echo "ArgoCD CLI 설치 중..."
    curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
    sudo install -m 555 /tmp/argocd /usr/local/bin/argocd
    rm /tmp/argocd
fi
echo -e "${GREEN}✅ ArgoCD CLI 준비됨${NC}"

# 2. ArgoCD 로그인
echo -e "\n${BLUE}2. ArgoCD 로그인${NC}"
argocd login $ARGOCD_SERVER --username admin --password $ARGOCD_PASSWORD --insecure --grpc-web

# 3. GitHub Repository 등록
echo -e "\n${BLUE}3. GitHub Repository 등록${NC}"
# SSH key 기반 인증 사용
argocd repo add git@github.com:$GITHUB_REPO.git --ssh-private-key-path ~/.ssh/id_rsa || true

# 4. ArgoCD Application 생성
echo -e "\n${BLUE}4. ArgoCD Application 생성${NC}"
cat > /tmp/argocd-app.yaml << EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: blacklist
  namespace: argocd
  annotations:
    # Image Updater 자동 설정
    argocd-image-updater.argoproj.io/image-list: blacklist=$REGISTRY/blacklist
    argocd-image-updater.argoproj.io/write-back-method: git
    argocd-image-updater.argoproj.io/git-branch: main
    argocd-image-updater.argoproj.io/blacklist.update-strategy: latest
    argocd-image-updater.argoproj.io/blacklist.allow-tags: 'regexp:^[0-9]{14}$'
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  
  source:
    repoURL: git@github.com:$GITHUB_REPO.git
    targetRevision: main
    path: k8s-gitops/overlays/prod
  
  destination:
    server: https://kubernetes.default.svc
    namespace: blacklist
  
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - ApplyOutOfSyncOnly=true
      - ServerSideApply=true
    
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  
  revisionHistoryLimit: 10
EOF

# ArgoCD에 Application 생성
kubectl apply -f /tmp/argocd-app.yaml

# 5. ArgoCD Image Updater 설치
echo -e "\n${BLUE}5. ArgoCD Image Updater 설치${NC}"
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml

# Image Updater 설정
cat > /tmp/argocd-image-updater-config.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-image-updater-config
  namespace: argocd
data:
  registries.conf: |
    registries:
    - name: registry.jclee.me
      api_url: http://registry.jclee.me
      prefix: registry.jclee.me
      insecure: yes
      default: true
  
  git.user: "ArgoCD Image Updater"
  git.email: "image-updater@argocd"
EOF

kubectl apply -f /tmp/argocd-image-updater-config.yaml

# Image Updater 재시작
kubectl rollout restart deployment/argocd-image-updater -n argocd

# 6. GitHub Webhook 설정
echo -e "\n${BLUE}6. GitHub Webhook 설정 안내${NC}"
echo "GitHub에서 다음 Webhook을 추가하세요:"
echo "URL: https://$ARGOCD_SERVER/api/webhook"
echo "Content type: application/json"
echo "Events: Push events, Pull request events"

# 7. 초기 동기화
echo -e "\n${BLUE}7. 초기 동기화${NC}"
argocd app sync blacklist --grpc-web

# 8. 자동화 테스트
echo -e "\n${BLUE}8. 자동화 테스트${NC}"
# 테스트 이미지 빌드 및 푸시
TEST_TAG=$(date +%Y%m%d%H%M%S)
echo "테스트 이미지 빌드: $REGISTRY/blacklist:$TEST_TAG"

docker build -f deployment/Dockerfile -t $REGISTRY/blacklist:$TEST_TAG .
docker push $REGISTRY/blacklist:$TEST_TAG

echo "10초 후 ArgoCD가 새 이미지를 감지합니다..."
sleep 10

# 상태 확인
argocd app get blacklist --grpc-web

# 9. 모니터링 설정
echo -e "\n${BLUE}9. 모니터링 자동화${NC}"
cat > /tmp/argocd-notifications.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  trigger.on-deployed: |
    - when: app.status.operationState.phase in ['Succeeded'] and app.status.health.status == 'Healthy'
      send: [webhook]
  
  trigger.on-health-degraded: |
    - when: app.status.health.status == 'Degraded'
      send: [webhook]
  
  trigger.on-sync-failed: |
    - when: app.status.operationState.phase in ['Error', 'Failed']
      send: [webhook]
  
  template.webhook: |
    webhook:
      webhook:
        url: ${WEBHOOK_URL}
        headers:
          - name: Content-Type
            value: application/json
    message: |
      {
        "app": "{{.app.metadata.name}}",
        "status": "{{.app.status.health.status}}",
        "sync": "{{.app.status.sync.status}}",
        "message": "{{.context.notificationType}}"
      }
EOF

kubectl apply -f /tmp/argocd-notifications.yaml

# 10. 완료
echo -e "\n${GREEN}=== GitOps 자동화 설정 완료 ===${NC}"
echo "✅ ArgoCD Application 생성됨"
echo "✅ Image Updater 설정됨 (2분마다 확인)"
echo "✅ 자동 동기화 활성화됨"
echo "✅ Self-healing 활성화됨"
echo ""
echo "이제 git push만 하면:"
echo "1. GitHub Actions가 Docker 이미지 빌드"
echo "2. Registry에 푸시"
echo "3. ArgoCD Image Updater가 감지"
echo "4. 자동으로 Kubernetes에 배포"
echo ""
echo "상태 확인: argocd app get blacklist --grpc-web"
echo "웹 UI: https://$ARGOCD_SERVER"