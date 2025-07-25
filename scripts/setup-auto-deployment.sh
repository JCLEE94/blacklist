#!/bin/bash

echo "===== 자동 배포 설정 스크립트 ====="
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. Docker Registry 인증 설정
echo -e "${YELLOW}1. Docker Registry 인증 설정${NC}"
echo "GitHub Actions에서 사용할 Docker Registry 인증 정보가 필요합니다."
echo ""

# 2. GitHub Actions 워크플로우 수정
echo -e "${YELLOW}2. GitHub Actions 워크플로우 업데이트${NC}"
cat > .github/workflows/auto-deploy.yaml << 'EOF'
name: Auto Deploy CI/CD
on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: self-hosted
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
        with:
          config-inline: |
            [registry."registry.jclee.me"]
              http = true
              insecure = true
      
      - name: Generate build metadata
        id: meta
        run: |
          echo "sha_short=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT
          echo "date=$(date +'%Y%m%d-%H%M%S')" >> $GITHUB_OUTPUT
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./deployment/Dockerfile
          push: true
          tags: |
            registry.jclee.me/jclee94/blacklist:latest
            registry.jclee.me/jclee94/blacklist:${{ steps.meta.outputs.sha_short }}
            registry.jclee.me/jclee94/blacklist:${{ steps.meta.outputs.date }}
          build-args: |
            BUILD_DATE=${{ steps.meta.outputs.date }}
            VCS_REF=${{ steps.meta.outputs.sha_short }}
      
      - name: Update Kubernetes deployment
        run: |
          # ArgoCD가 자동으로 감지하도록 annotation 업데이트
          kubectl annotate deployment blacklist -n blacklist \
            kubernetes.io/change-cause="Auto deploy: ${{ steps.meta.outputs.sha_short }}" \
            --overwrite
EOF

echo -e "${GREEN}✅ GitHub Actions 워크플로우 생성됨${NC}"

# 3. ArgoCD 자동 동기화 설정
echo ""
echo -e "${YELLOW}3. ArgoCD 자동 동기화 활성화${NC}"

cat > argocd-auto-sync.yaml << 'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: blacklist
  namespace: argocd
  annotations:
    argocd-image-updater.argoproj.io/image-list: blacklist=registry.jclee.me/jclee94/blacklist
    argocd-image-updater.argoproj.io/update-strategy: latest
    argocd-image-updater.argoproj.io/write-back-method: git
spec:
  project: default
  source:
    repoURL: https://charts.jclee.me
    chart: blacklist
    targetRevision: "*"
    helm:
      releaseName: blacklist
      values: |
        image:
          repository: registry.jclee.me/jclee94/blacklist
          tag: latest
          pullPolicy: Always
        persistence:
          enabled: true
          storageClass: local-path
          size: 5Gi
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
    - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
EOF

# 4. ArgoCD Image Updater 설정
echo ""
echo -e "${YELLOW}4. ArgoCD Image Updater ConfigMap 생성${NC}"

cat > argocd-image-updater-config.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-image-updater-config
  namespace: argocd
data:
  registries.conf: |
    registries:
    - name: registry.jclee.me
      api_url: https://registry.jclee.me
      prefix: registry.jclee.me
      insecure: yes
      default: true
  log.level: debug
EOF

# 5. 배포 스크립트
echo ""
echo -e "${YELLOW}5. 간편 배포 스크립트 생성${NC}"

cat > deploy.sh << 'EOF'
#!/bin/bash
# 간편 배포 스크립트

echo "🚀 배포 시작..."

# Git 상태 확인
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  커밋되지 않은 변경사항이 있습니다."
    read -p "계속하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 변경사항 커밋 및 푸시
git add -A
git commit -m "chore: auto deployment $(date +'%Y-%m-%d %H:%M:%S')"
git push origin main

echo "✅ GitHub에 푸시 완료"
echo "⏳ CI/CD 파이프라인이 자동으로 실행됩니다..."
echo ""
echo "진행 상황 확인:"
echo "- GitHub Actions: https://github.com/JCLEE94/blacklist/actions"
echo "- ArgoCD: kubectl get app blacklist -n argocd"
echo "- Pod 상태: kubectl get pods -n blacklist -w"
EOF

chmod +x deploy.sh

# 6. 설정 적용
echo ""
echo -e "${YELLOW}6. 설정 적용 중...${NC}"

# ArgoCD Image Updater ConfigMap 적용
kubectl apply -f argocd-image-updater-config.yaml

# ArgoCD 애플리케이션 업데이트
kubectl apply -f argocd-auto-sync.yaml

echo ""
echo -e "${GREEN}===== 자동 배포 설정 완료 =====${NC}"
echo ""
echo "📋 설정 요약:"
echo "1. GitHub Actions: 자동 빌드 및 푸시"
echo "2. ArgoCD: 자동 동기화 활성화"
echo "3. Image Updater: 새 이미지 자동 감지"
echo "4. 배포 명령: ./deploy.sh"
echo ""
echo "⚠️  주의사항:"
echo "- PVC 데이터는 보존됩니다"
echo "- 롤백: kubectl rollout undo deployment/blacklist -n blacklist"
echo "- 수동 동기화 복원: kubectl patch app blacklist -n argocd --type='json' -p='[{\"op\": \"remove\", \"path\": \"/spec/syncPolicy/automated\"}]'"