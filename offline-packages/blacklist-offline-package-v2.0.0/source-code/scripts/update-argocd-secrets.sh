#\!/bin/bash

echo "🔐 ArgoCD 시크릿 현행화 스크립트"

# ArgoCD 서버 정보
ARGOCD_SERVER="192.168.50.110:31017"
ARGOCD_USER="admin"

echo "📝 ArgoCD 로그인 중..."
# ArgoCD CLI로 로그인 (비밀번호는 프롬프트로 입력)
argocd login $ARGOCD_SERVER --username $ARGOCD_USER --grpc-web --insecure

echo "🔑 새 토큰 생성 중..."
# 새 API 토큰 생성
NEW_TOKEN=$(argocd account generate-token --account $ARGOCD_USER --id github-actions-$(date +%Y%m%d) --grpc-web)

if [ -z "$NEW_TOKEN" ]; then
    echo "❌ 토큰 생성 실패"
    exit 1
fi

echo "✅ 새 토큰 생성 완료"
echo "🔧 GitHub Secret 업데이트 중..."

# GitHub Secret 업데이트
gh secret set ARGOCD_TOKEN --body "$NEW_TOKEN"
gh secret set ARGOCD_AUTH_TOKEN --body "$NEW_TOKEN"

# 추가 시크릿 업데이트
gh secret set ARGOCD_SERVER --body "$ARGOCD_SERVER"
gh secret set ARGOCD_URL --body "http://$ARGOCD_SERVER"
gh secret set ARGOCD_USERNAME --body "$ARGOCD_USER"

echo "✅ ArgoCD 시크릿 현행화 완료\!"
echo ""
echo "📋 업데이트된 시크릿:"
echo "  - ARGOCD_TOKEN"
echo "  - ARGOCD_AUTH_TOKEN"
echo "  - ARGOCD_SERVER: $ARGOCD_SERVER"
echo "  - ARGOCD_URL: http://$ARGOCD_SERVER"
echo "  - ARGOCD_USERNAME: $ARGOCD_USER"
