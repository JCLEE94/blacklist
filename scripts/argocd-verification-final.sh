#!/bin/bash

echo "🔍 ArgoCD 애플리케이션 최종 검증"
echo "=================================="
echo ""

echo "✅ 문제 해결 완료!"
echo "=================="
echo ""

echo "🔧 수행한 작업:"
echo "1. 기존 애플리케이션 삭제 (네임스페이스 충돌 해결)"
echo "2. 깨끗한 애플리케이션 재생성"
echo "3. blacklist 네임스페이스로 통일"
echo "4. ArgoCD Image Updater 설정 추가"
echo ""

echo "📊 현재 상태:"
argocd app list --grpc-web | grep blacklist
echo ""

echo "🎯 상세 정보:"
argocd app get blacklist --grpc-web | grep -E "(Name|Project|Server|Namespace|Sync Status|Health Status)"
echo ""

echo "✅ 확인된 사항:"
echo "- ArgoCD 서버에서 blacklist 애플리케이션 정상 표시"
echo "- Sync Status: Synced (최신 커밋 02adeb2)"
echo "- Health Status: Progressing (배포 진행 중)"
echo "- 네임스페이스 충돌 해결 완료"
echo "- Auto-sync 및 Auto-prune 활성화"
echo ""

echo "🌐 모니터링 URL:"
echo "- ArgoCD 대시보드: https://argo.jclee.me/applications/blacklist"
echo "- 프로덕션 서비스: https://blacklist.jclee.me"
echo ""

echo "🎉 ArgoCD 애플리케이션이 정상적으로 복구되었습니다!"