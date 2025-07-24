#!/bin/bash
# CI/CD 즉시 수정 스크립트

echo "=== CI/CD 즉시 수정 ==="
echo ""

# 1. 실행 권한 설정
echo "1. 스크립트 실행 권한 설정"
chmod +x scripts/*.sh
echo "✅ 완료"
echo ""

# 2. Git 설정
echo "2. Git 설정"
git config user.name "JCLEE94"
git config user.email "your-email@example.com"
echo "✅ 완료"
echo ""

# 3. 변경사항 커밋
echo "3. CI/CD 수정사항 커밋"
git add -A
git commit -m "fix: CI/CD 단순화 - registry 인증 제거, simple-cicd 추가" || echo "변경사항 없음"
echo ""

# 4. Push
echo "4. GitHub에 Push"
git push origin main || echo "Push 실패 - 수동으로 실행 필요"
echo ""

# 5. ArgoCD 설정 안내
echo "5. ArgoCD 설정 (수동 실행 필요)"
echo "-----------------------------------"
echo "kubectl apply -f k8s-gitops/argocd/blacklist-app-https.yaml"
echo ""

echo "=== 완료 ==="
echo ""
echo "다음 확인사항:"
echo "1. GitHub Actions: https://github.com/JCLEE94/blacklist/actions"
echo "2. 두 가지 워크플로우 사용 가능:"
echo "   - gitops-cicd.yml (수정됨)"
echo "   - simple-cicd.yml (새로 생성)"
echo "3. ArgoCD가 HTTPS로 저장소 접근하도록 변경됨"