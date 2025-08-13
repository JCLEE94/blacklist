#!/bin/bash
# GitHub Webhook 및 자동 배포 설정 스크립트

echo "🔗 GitHub Webhook 및 자동 배포 설정..."

# 설정 변수
NAMESPACE="blacklist"
GITHUB_TOKEN="${GITHUB_TOKEN}"
GITHUB_REPO="JCLEE94/blacklist"
WEBHOOK_URL="${WEBHOOK_URL:-http://webhook-service.default.svc.cluster.local/hook}"

# 1. Webhook 서비스 생성
echo "📡 Webhook 서비스 배포..."
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-handler
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: webhook-handler
  template:
    metadata:
      labels:
        app: webhook-handler
    spec:
      containers:
      - name: webhook
        image: adnanh/webhook:latest
        ports:
        - containerPort: 9000
        volumeMounts:
        - name: webhook-config
          mountPath: /etc/webhook
        command: ["/usr/local/bin/webhook"]
        args: ["-hooks", "/etc/webhook/hooks.json", "-verbose"]
      volumes:
      - name: webhook-config
        configMap:
          name: webhook-config
---
apiVersion: v1
kind: Service
metadata:
  name: webhook-service
  namespace: default
spec:
  selector:
    app: webhook-handler
  ports:
  - port: 80
    targetPort: 9000
  type: ClusterIP
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: webhook-config
  namespace: default
data:
  hooks.json: |
    [
      {
        "id": "blacklist-deploy",
        "execute-command": "/usr/local/bin/deploy.sh",
        "command-working-directory": "/tmp",
        "pass-arguments-to-command": [
          {
            "source": "payload",
            "name": "head_commit.id"
          },
          {
            "source": "payload",  
            "name": "ref"
          }
        ],
        "trigger-rule": {
          "and": [
            {
              "match": {
                "type": "payload-hash-sha1",
                "secret": "github-webhook-secret",
                "parameter": {
                  "source": "header",
                  "name": "X-Hub-Signature"
                }
              }
            },
            {
              "match": {
                "type": "value",
                "value": "refs/heads/main",
                "parameter": {
                  "source": "payload",
                  "name": "ref"
                }
              }
            }
          ]
        }
      }
    ]
  deploy.sh: |
    #!/bin/bash
    echo "🚀 Webhook 트리거 배포 시작..."
    
    COMMIT_SHA=\$1
    REF=\$2
    SHORT_SHA=\${COMMIT_SHA:0:8}
    
    echo "📋 배포 정보:"
    echo "   - Commit: \$SHORT_SHA"
    echo "   - Ref: \$REF"
    
    # kubectl 명령으로 이미지 업데이트
    kubectl set image deployment/blacklist \\
      blacklist=registry.jclee.me/blacklist:\$SHORT_SHA \\
      -n blacklist
    
    # 롤아웃 재시작
    kubectl rollout restart deployment/blacklist -n blacklist
    
    # 상태 확인
    kubectl rollout status deployment/blacklist -n blacklist --timeout=300s
    
    echo "✅ Webhook 배포 완료!"
EOF

# ConfigMap에 실행 권한 설정
kubectl create configmap webhook-deploy-script \
  --from-file=deploy.sh=/tmp/deploy.sh \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. GitHub Webhook 등록 (GitHub CLI 필요)
if command -v gh &> /dev/null && [ -n "$GITHUB_TOKEN" ]; then
    echo "🔗 GitHub Webhook 등록..."
    
    # Webhook URL 가져오기 (LoadBalancer나 Ingress 설정 필요)
    WEBHOOK_ENDPOINT="https://your-domain.com/webhook/blacklist-deploy"
    
    gh api repos/$GITHUB_REPO/hooks \
      --method POST \
      --field name='web' \
      --field active=true \
      --field config[url]="$WEBHOOK_ENDPOINT" \
      --field config[content_type]='json' \
      --field config[secret]='github-webhook-secret' \
      --field events[]='push'
    
    echo "✅ GitHub Webhook 등록 완료"
else
    echo "⚠️ GitHub CLI가 없거나 토큰이 설정되지 않음"
    echo "수동으로 GitHub Webhook 설정:"
    echo "   URL: $WEBHOOK_ENDPOINT"
    echo "   Content type: application/json"
    echo "   Secret: github-webhook-secret"
    echo "   Events: push"
fi

# 3. ArgoCD Image Updater 설정 (선택사항)
if kubectl get namespace argocd &>/dev/null; then
    echo "🔄 ArgoCD Image Updater 설정..."
    
    # ArgoCD Image Updater 배포
    kubectl apply -f argocd/image-updater-config.yaml
    
    # ArgoCD Application 생성
    kubectl apply -f argocd/application.yaml
    
    echo "✅ ArgoCD 설정 완료"
else
    echo "⚠️ ArgoCD가 설치되지 않음 - 스킵"
fi

echo "
=====================================
🎉 자동 배포 설정 완료!
=====================================

설정된 구성요소:
✅ Webhook Handler 서비스
✅ GitHub Push 이벤트 처리
✅ 자동 이미지 업데이트

작동 방식:
1. GitHub에 Push → GitHub Actions 빌드 & Registry 푸시
2. ArgoCD Image Updater → 새 이미지 감지 & 자동 배포
3. 또는 Webhook → 즉시 배포 트리거

확인 명령어:
- kubectl get pods -n default -l app=webhook-handler
- kubectl logs -f deployment/webhook-handler -n default
- kubectl get application -n argocd (ArgoCD 설치된 경우)
=====================================
"