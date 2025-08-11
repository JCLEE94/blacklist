#!/bin/bash

# ArgoCD GitHub Token 업데이트 스크립트
# =====================================

set -e

echo "🔐 ArgoCD GitHub Token 업데이트"
echo "================================"

# 환경 변수 설정
ARGOCD_SERVER=${ARGOCD_SERVER:-argo.jclee.me}
ARGOCD_NAMESPACE=${ARGOCD_NAMESPACE:-argocd}
REPO_URL="https://github.com/JCLEE94/blacklist"

# GitHub Token 입력
echo -n "GitHub Personal Access Token을 입력하세요: "
read -s GITHUB_TOKEN
echo

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GitHub Token이 입력되지 않았습니다."
    exit 1
fi

# ArgoCD 로그인 확인
echo "📋 ArgoCD 서버 연결 확인..."
if command -v argocd &> /dev/null; then
    # ArgoCD CLI가 있는 경우
    echo "ArgoCD CLI를 사용하여 연결합니다..."
    
    # ArgoCD 로그인 (이미 로그인되어 있을 수 있음)
    argocd login $ARGOCD_SERVER --grpc-web || true
    
    # Repository Secret 업데이트
    echo "🔄 Repository Secret 업데이트..."
    argocd repo add $REPO_URL \
        --username x-access-token \
        --password $GITHUB_TOKEN \
        --upsert \
        --grpc-web
    
    echo "✅ ArgoCD Repository에 GitHub Token이 업데이트되었습니다."
    
    # Repository 목록 확인
    echo -e "\n📋 등록된 Repository 목록:"
    argocd repo list --grpc-web | grep blacklist || true
    
elif command -v kubectl &> /dev/null; then
    # kubectl을 사용한 Secret 업데이트
    echo "kubectl을 사용하여 Secret을 업데이트합니다..."
    
    # Secret 생성/업데이트
    kubectl create secret generic repo-blacklist \
        --from-literal=type=git \
        --from-literal=url=$REPO_URL \
        --from-literal=username=x-access-token \
        --from-literal=password=$GITHUB_TOKEN \
        --namespace=$ARGOCD_NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Secret에 레이블 추가
    kubectl label secret repo-blacklist \
        argocd.argoproj.io/secret-type=repository \
        --namespace=$ARGOCD_NAMESPACE \
        --overwrite
    
    echo "✅ Kubernetes Secret이 업데이트되었습니다."
    
    # Secret 확인
    echo -e "\n📋 Secret 상태:"
    kubectl get secret repo-blacklist -n $ARGOCD_NAMESPACE
    
else
    # 수동 설정 가이드
    echo "⚠️ ArgoCD CLI 또는 kubectl이 설치되지 않았습니다."
    echo ""
    echo "다음 방법 중 하나로 GitHub Token을 설정하세요:"
    echo ""
    echo "1. ArgoCD Web UI에서 설정:"
    echo "   - https://$ARGOCD_SERVER 접속"
    echo "   - Settings → Repositories → Connect Repo"
    echo "   - Connection Method: HTTPS"
    echo "   - Repository URL: $REPO_URL"
    echo "   - Username: x-access-token"
    echo "   - Password: [GitHub Token]"
    echo ""
    echo "2. kubectl 명령어로 설정:"
    cat <<EOF
kubectl create secret generic repo-blacklist \\
  --from-literal=type=git \\
  --from-literal=url=$REPO_URL \\
  --from-literal=username=x-access-token \\
  --from-literal=password=$GITHUB_TOKEN \\
  --namespace=$ARGOCD_NAMESPACE

kubectl label secret repo-blacklist \\
  argocd.argoproj.io/secret-type=repository \\
  --namespace=$ARGOCD_NAMESPACE
EOF
fi

# Application 동기화 트리거
echo -e "\n🔄 Application 동기화 트리거..."

if command -v argocd &> /dev/null; then
    # 모든 환경의 Application 동기화
    for env in production staging development; do
        APP_NAME="blacklist-$env"
        echo "동기화: $APP_NAME"
        argocd app sync $APP_NAME --grpc-web 2>/dev/null || echo "  $APP_NAME이 존재하지 않거나 동기화할 수 없습니다."
    done
fi

echo -e "\n✅ GitHub Token 업데이트 완료!"
echo ""
echo "📋 다음 단계:"
echo "1. ArgoCD Web UI에서 Repository 연결 확인"
echo "   https://$ARGOCD_SERVER/settings/repos"
echo ""
echo "2. Application 동기화 상태 확인"
echo "   https://$ARGOCD_SERVER/applications"
echo ""
echo "3. 배포 검증 실행"
echo "   ./scripts/verify-deployment.sh"

# GitHub Token 정보 저장 (선택사항)
echo -e "\n💾 GitHub Token을 로컬에 저장하시겠습니까? (보안 주의) [y/N]: "
read -r SAVE_TOKEN

if [[ "$SAVE_TOKEN" =~ ^[Yy]$ ]]; then
    # .env.argocd 파일에 저장
    cat > .env.argocd <<EOF
# ArgoCD GitHub Token Configuration
# ⚠️ 보안 주의: 이 파일을 Git에 커밋하지 마세요!
GITHUB_TOKEN=$GITHUB_TOKEN
ARGOCD_SERVER=$ARGOCD_SERVER
REPO_URL=$REPO_URL
EOF
    chmod 600 .env.argocd
    echo "✅ Token이 .env.argocd에 저장되었습니다. (권한: 600)"
    echo "⚠️ 주의: .env.argocd 파일을 절대 Git에 커밋하지 마세요!"
    
    # .gitignore에 추가
    if ! grep -q ".env.argocd" .gitignore 2>/dev/null; then
        echo ".env.argocd" >> .gitignore
        echo "✅ .gitignore에 .env.argocd 추가됨"
    fi
fi

echo -e "\n🎉 모든 설정이 완료되었습니다!"