#!/bin/bash

# GitOps 배포 템플릿 기반 kubeconfig 생성 스크립트
# 이 스크립트는 K8s 클러스터 접속을 위한 kubeconfig 파일을 생성합니다.

set -e

# === 환경 변수 설정 ===
K8S_TOKEN="${K8S_TOKEN:-eyJhbGciOiJSUzI1NiIsImtpZCI6Ikxobzd5NUhuUmV0S0pJQTkwN1F5dUZtcDdUeXlKRTdSX2t6NGo0ZWlmUUUifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWFjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJjbHVzdGVyLWFkbWluLXRva2VuIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWFjY291bnQuc2VydmljZS1hY2NvdW50Lm5hbWUiOiJjbHVzdGVyLWFkbWluLXNhIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjM1ZWY0NDExLTU2NGItNDI2Mi04MzU2LTlhMjliMTk2ZDM1ZCIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDprdWJlLXN5c3RlbTpjbHVzdGVyLWFkbWluLXNhIn0.Fy3KcosO8gc_npEwxIjCi3d1bjEl6A8SsJ7NvAuiURkzhhpOiyV3MPjQ1-MjD6Len3OSP_OZMAnxlwONAoBHnUVXdhyAbEUk-TgKN9gwztaIiEboTf3AknhgSUJnZreGQKfipwOxZJ3gBzSVKbcaJ9zlDBDPwvrdNaEmvU9LNu5-pUgG0taAfJoWYFzZmBjH7LjioZdIqM1E5TjuIxVcPUOLh-CMF_5BdOk4s7eAvy3guBcXsvNHxCx8ZFuSOd4DwutU6YLrZ0f9sFol_w_oX3HNfpbwKmwoDoNNzYESnr66--QJLToI7RsLjMrgeWbwRkuFXGxyBt_oGyFn2bCfkA}"
K8S_CLUSTER="${K8S_CLUSTER:-https://k8s.jclee.me:443}"
KUBECONFIG_FILE="${KUBECONFIG_FILE:-$HOME/.kube/config-k8s-jclee}"

echo "📋 Kubeconfig 생성 시작..."

# 디렉토리 생성
mkdir -p $(dirname "$KUBECONFIG_FILE")

# Kubeconfig 파일 생성
cat > "$KUBECONFIG_FILE" << EOF
apiVersion: v1
kind: Config
clusters:
- cluster:
    insecure-skip-tls-verify: true
    server: ${K8S_CLUSTER}
  name: k8s-jclee
contexts:
- context:
    cluster: k8s-jclee
    namespace: blacklist
    user: cluster-admin
  name: k8s-jclee-admin
current-context: k8s-jclee-admin
users:
- name: cluster-admin
  user:
    token: ${K8S_TOKEN}
EOF

echo "✅ Kubeconfig 파일이 생성되었습니다: $KUBECONFIG_FILE"

# 연결 테스트
echo "🔍 클러스터 연결 테스트..."
if KUBECONFIG="$KUBECONFIG_FILE" kubectl cluster-info &>/dev/null; then
    echo "✅ 클러스터 연결 성공"
    echo ""
    echo "사용 방법:"
    echo "  export KUBECONFIG=$KUBECONFIG_FILE"
    echo "  kubectl get nodes"
else
    echo "❌ 클러스터 연결 실패. 토큰과 클러스터 URL을 확인하세요."
    exit 1
fi