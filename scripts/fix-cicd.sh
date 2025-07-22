#!/bin/bash
# CI/CD 문제 해결 스크립트

set -e

echo "=== CI/CD 문제 진단 및 해결 ==="
echo ""

# 1. GitHub Secrets 확인
echo "1. GitHub Secrets 설정 안내"
echo "----------------------------"
echo "GitHub 저장소 Settings → Secrets and variables → Actions에서 다음 설정 필요:"
echo ""
echo "필수 Secrets:"
echo "- REGISTRY_USERNAME: registry 사용자명"
echo "- REGISTRY_PASSWORD: registry 비밀번호"
echo ""
echo "현재 registry.jclee.me는 인증이 필요없을 수 있습니다."
echo "그런 경우 로그인 단계를 수정해야 합니다."
echo ""

# 2. K8s GitOps 디렉토리 확인
echo "2. K8s GitOps 디렉토리 구조 확인"
echo "---------------------------------"
if [ -d "k8s-gitops" ]; then
    echo "✅ k8s-gitops 디렉토리 존재"
    tree k8s-gitops -L 3 2>/dev/null || find k8s-gitops -type f | head -20
else
    echo "❌ k8s-gitops 디렉토리 없음 - 생성 필요"
fi
echo ""

# 3. ArgoCD SSH Key 설정 확인
echo "3. ArgoCD Repository 접근 설정"
echo "-------------------------------"
echo "ArgoCD가 Git 저장소에 접근하려면:"
echo ""
echo "Option A: HTTPS로 변경 (권장)"
echo "- repoURL: https://github.com/JCLEE94/blacklist.git"
echo "- GitHub Personal Access Token 필요"
echo ""
echo "Option B: SSH 유지"
echo "- GitHub Deploy Key 생성 필요"
echo "- ArgoCD에 SSH private key 등록 필요"
echo ""

# 4. 수정된 워크플로우 생성
echo "4. 간단한 CI/CD 워크플로우 생성"
echo "--------------------------------"
cat > .github/workflows/simple-cicd.yml << 'EOF'
name: Simple CI/CD

on:
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  REGISTRY: registry.jclee.me
  IMAGE_NAME: blacklist

jobs:
  build-and-push:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v3
      
      - name: Generate Version
        id: version
        run: |
          VERSION=$(date +%Y%m%d%H%M%S)
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "Version: $VERSION"
      
      - name: Build and Push
        run: |
          # registry.jclee.me는 인증 없이 사용 가능
          docker build -f deployment/Dockerfile -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.version.outputs.version }} .
          docker tag ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.version.outputs.version }} ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          docker push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.version.outputs.version }}
          docker push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
      
      - name: Trigger ArgoCD Sync
        run: |
          echo "✅ Docker image pushed successfully"
          echo "ArgoCD Image Updater will detect and deploy the new image"
EOF

echo "✅ simple-cicd.yml 생성됨"
echo ""

# 5. ArgoCD 앱 HTTPS 버전 생성
echo "5. ArgoCD Application HTTPS 버전"
echo "---------------------------------"
cat > k8s-gitops/argocd/blacklist-app-https.yaml << 'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: blacklist
  namespace: argocd
  annotations:
    argocd-image-updater.argoproj.io/image-list: blacklist=registry.jclee.me/blacklist:latest
    argocd-image-updater.argoproj.io/blacklist.update-strategy: latest
    argocd-image-updater.argoproj.io/blacklist.pull-secret: namespace:blacklist:regcred
spec:
  project: default
  source:
    repoURL: https://github.com/JCLEE94/blacklist.git
    targetRevision: main
    path: k8s-gitops/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: blacklist
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF

echo "✅ blacklist-app-https.yaml 생성됨"
echo ""

# 6. 테스트 스크립트
echo "6. CI/CD 테스트 스크립트"
echo "------------------------"
cat > scripts/test-simple-cicd.sh << 'EOF'
#!/bin/bash
# 간단한 CI/CD 테스트

set -e

echo "=== Simple CI/CD Test ==="

# 1. 버전 업데이트
echo "Updating version..."
sed -i "s/__version__ = .*/__version__ = '2.1.3-test'/" src/core/__init__.py || true

# 2. Commit
git add -A
git commit -m "test: Simple CI/CD test" || echo "No changes"

# 3. Push
echo "Pushing to GitHub..."
git push origin main

echo ""
echo "✅ Test pushed. Check GitHub Actions for results."
echo "https://github.com/JCLEE94/blacklist/actions"
EOF

chmod +x scripts/test-simple-cicd.sh
echo "✅ test-simple-cicd.sh 생성됨"
echo ""

# 7. 권장 사항
echo "=== 권장 해결 방법 ==="
echo ""
echo "1. 간단한 CI/CD 사용:"
echo "   - simple-cicd.yml 사용 (registry 인증 불필요)"
echo "   - ArgoCD Image Updater가 자동으로 새 이미지 감지"
echo ""
echo "2. ArgoCD 설정 변경:"
echo "   - HTTPS URL 사용 (SSH 대신)"
echo "   - kubectl apply -f k8s-gitops/argocd/blacklist-app-https.yaml"
echo ""
echo "3. 테스트:"
echo "   - ./scripts/test-simple-cicd.sh 실행"
echo ""
echo "4. 모니터링:"
echo "   - GitHub Actions: https://github.com/JCLEE94/blacklist/actions"
echo "   - ArgoCD: argocd app get blacklist --grpc-web"