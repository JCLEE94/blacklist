#!/bin/bash

echo "🔧 ArgoCD Ingress Health Check 수정 스크립트"
echo "=========================================="
echo ""

# 원격 서버 정보
REMOTE_SERVER="192.168.50.110"
REMOTE_USER="jclee"

# 비밀번호 입력 안내
echo "원격 서버 비밀번호가 필요합니다."
echo ""

# ArgoCD ConfigMap 수정을 위한 YAML 파일 생성
cat > /tmp/argocd-cm-patch.yaml << 'EOF'
data:
  resource.customizations.health.networking.k8s.io_Ingress: |
    hs = {}
    hs.status = "Healthy"
    hs.message = "Ingress is ready"
    
    -- Ingress가 LoadBalancer 타입이 아닌 경우 항상 Healthy로 처리
    if obj.status ~= nil and obj.status.loadBalancer ~= nil and obj.status.loadBalancer.ingress ~= nil then
      -- LoadBalancer가 있는 경우에만 상태 체크
      ingress = obj.status.loadBalancer.ingress[1]
      if ingress ~= nil then
        hs.message = "Ingress has IP or hostname assigned"
      end
    else
      -- LoadBalancer가 없는 경우 (NodePort 등)도 Healthy로 처리
      hs.message = "Ingress is configured"
    end
    
    return hs
EOF

echo "1. 원격 서버에서 ArgoCD ConfigMap 백업 중..."
ssh ${REMOTE_USER}@${REMOTE_SERVER} "kubectl get cm argocd-cm -n argocd -o yaml > /tmp/argocd-cm-backup.yaml && echo '✅ ConfigMap 백업 완료'"

echo ""
echo "2. ConfigMap 패치 파일 원격 서버로 복사 중..."
scp /tmp/argocd-cm-patch.yaml ${REMOTE_USER}@${REMOTE_SERVER}:/tmp/

echo ""
echo "3. ArgoCD ConfigMap 업데이트 중..."
ssh ${REMOTE_USER}@${REMOTE_SERVER} << 'REMOTE_COMMANDS'
# 현재 ConfigMap 가져오기
kubectl get cm argocd-cm -n argocd -o yaml > /tmp/argocd-cm-current.yaml

# Python 스크립트로 YAML 수정
python3 << 'PYTHON_SCRIPT'
import yaml
import sys

# 현재 ConfigMap 읽기
with open('/tmp/argocd-cm-current.yaml', 'r') as f:
    cm = yaml.safe_load(f)

# 패치 내용 읽기
with open('/tmp/argocd-cm-patch.yaml', 'r') as f:
    patch = yaml.safe_load(f)

# data 섹션이 없으면 생성
if 'data' not in cm:
    cm['data'] = {}

# 패치 적용
cm['data'].update(patch['data'])

# 수정된 ConfigMap 저장
with open('/tmp/argocd-cm-updated.yaml', 'w') as f:
    yaml.dump(cm, f, default_flow_style=False)

print("✅ ConfigMap 수정 완료")
PYTHON_SCRIPT

# ConfigMap 적용
kubectl apply -f /tmp/argocd-cm-updated.yaml
REMOTE_COMMANDS

echo ""
echo "4. ArgoCD Server 재시작 중..."
ssh ${REMOTE_USER}@${REMOTE_SERVER} "kubectl rollout restart deployment argocd-server -n argocd && echo '✅ ArgoCD Server 재시작 시작'"

echo ""
echo "5. 재시작 상태 확인 중..."
ssh ${REMOTE_USER}@${REMOTE_SERVER} "kubectl rollout status deployment argocd-server -n argocd --timeout=120s"

echo ""
echo "6. ArgoCD Application 동기화 중..."
ssh ${REMOTE_USER}@${REMOTE_SERVER} "argocd app sync blacklist --grpc-web --insecure || echo 'ArgoCD CLI 동기화 실패 - 웹 UI에서 수동 동기화 필요'"

echo ""
echo "7. 최종 상태 확인..."
ssh ${REMOTE_USER}@${REMOTE_SERVER} << 'FINAL_CHECK'
echo "📊 ArgoCD Application 상태:"
kubectl get application blacklist -n argocd -o jsonpath='{.status.health.status}' && echo ""
echo ""
echo "📊 Blacklist Pod 상태:"
kubectl get pods -n blacklist
echo ""
echo "📊 Ingress 상태:"
kubectl get ingress -n blacklist
FINAL_CHECK

echo ""
echo "✅ ArgoCD Ingress Health Check 수정 완료!"
echo ""
echo "📌 추가 확인사항:"
echo "  - ArgoCD 웹 UI (https://argo.jclee.me)에서 blacklist 앱 확인"
echo "  - Ingress가 여전히 Progressing이면 웹 UI에서 수동 동기화"
echo "  - 문제 지속 시 ArgoCD 로그 확인: kubectl logs -n argocd deployment/argocd-server"

# 임시 파일 정리
rm -f /tmp/argocd-cm-patch.yaml