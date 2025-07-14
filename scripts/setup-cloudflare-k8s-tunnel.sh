#!/bin/bash

# Cloudflare Tunnel for Kubernetes Internal Services
# Kubernetes 내부 DNS를 외부에서 접속 가능하게 만드는 스크립트

set -e

echo "🚀 Cloudflare Tunnel을 통한 Kubernetes 내부 서비스 접속 설정"
echo ""

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 설정
NAMESPACE="blacklist"
TUNNEL_NAME="blacklist-k8s-internal"

echo -e "${BLUE}이 설정을 통해 다음 주소들이 외부에서 접속 가능해집니다:${NC}"
echo "- https://blacklist-svc.jclee.me → blacklist.blacklist.svc.cluster.local:2541"
echo "- https://blacklist-nodeport.jclee.me → blacklist-nodeport.blacklist.svc.cluster.local:2541"
echo ""

echo -e "${YELLOW}📌 Cloudflare Zero Trust 설정 단계:${NC}"
echo ""
echo "1. https://one.dash.cloudflare.com/ 로그인"
echo ""
echo "2. Access > Tunnels 메뉴"
echo ""
echo "3. 'Create a tunnel' 클릭"
echo "   - Tunnel 이름: $TUNNEL_NAME"
echo ""
echo "4. 토큰 복사 후 아래 명령 실행:"
echo -e "${GREEN}export CLOUDFLARE_TUNNEL_TOKEN='복사한_토큰'${NC}"
echo ""
echo "5. Public Hostname 설정 (2개 추가):"
echo ""
echo "   ${BLUE}[첫 번째 호스트네임]${NC}"
echo "   - Subdomain: blacklist-svc"
echo "   - Domain: jclee.me"
echo "   - Type: HTTP"
echo "   - URL: blacklist.blacklist.svc.cluster.local:2541"
echo ""
echo "   ${BLUE}[두 번째 호스트네임]${NC}"
echo "   - Subdomain: blacklist-nodeport"
echo "   - Domain: jclee.me"
echo "   - Type: HTTP"
echo "   - URL: blacklist-nodeport.blacklist.svc.cluster.local:2541"
echo ""
echo "6. Save tunnel 클릭"
echo ""

# 토큰 확인
if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
    echo -e "${RED}❌ CLOUDFLARE_TUNNEL_TOKEN이 설정되지 않았습니다${NC}"
    echo "위 안내를 따라 설정 후 다시 실행하세요."
    exit 1
fi

echo -e "${GREEN}✅ 토큰 확인됨. Kubernetes에 배포합니다...${NC}"

# Cloudflare Tunnel 배포
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: cloudflared-config
  namespace: $NAMESPACE
data:
  config.yaml: |
    tunnel: $TUNNEL_NAME
    credentials-file: /etc/cloudflared/creds/token
    no-autoupdate: true
    metrics: 0.0.0.0:2000
    
    ingress:
      - hostname: blacklist-svc.jclee.me
        service: http://blacklist.blacklist.svc.cluster.local:2541
      - hostname: blacklist-nodeport.jclee.me  
        service: http://blacklist-nodeport.blacklist.svc.cluster.local:2541
      - service: http_status:404
---
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-tunnel-token
  namespace: $NAMESPACE
type: Opaque
stringData:
  token: "$CLOUDFLARE_TUNNEL_TOKEN"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudflared
  namespace: $NAMESPACE
  labels:
    app: cloudflared
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cloudflared
  template:
    metadata:
      labels:
        app: cloudflared
    spec:
      containers:
      - name: cloudflared
        image: cloudflare/cloudflared:latest
        args:
        - tunnel
        - --config
        - /etc/cloudflared/config/config.yaml
        - --no-autoupdate
        - run
        env:
        - name: TUNNEL_TOKEN
          valueFrom:
            secretKeyRef:
              name: cloudflare-tunnel-token
              key: token
        volumeMounts:
        - name: config
          mountPath: /etc/cloudflared/config
          readOnly: true
        - name: creds
          mountPath: /etc/cloudflared/creds
          readOnly: true
        resources:
          requests:
            cpu: 10m
            memory: 20Mi
          limits:
            cpu: 100m  
            memory: 256Mi
        livenessProbe:
          httpGet:
            path: /ready
            port: 2000
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: cloudflared-config
      - name: creds
        secret:
          secretName: cloudflare-tunnel-token
          items:
          - key: token
            path: token
EOF

echo ""
echo -e "${GREEN}✅ Cloudflare Tunnel 배포 완료!${NC}"
echo ""
echo "Pod 상태 확인:"
echo "kubectl get pods -n $NAMESPACE -l app=cloudflared"
echo ""
echo "로그 확인:"
echo "kubectl logs -n $NAMESPACE -l app=cloudflared -f"
echo ""
echo -e "${BLUE}접속 가능한 주소:${NC}"
echo "- https://blacklist-svc.jclee.me (내부: blacklist.blacklist.svc.cluster.local:2541)"
echo "- https://blacklist-nodeport.jclee.me (내부: blacklist-nodeport.blacklist.svc.cluster.local:2541)"
echo ""
echo -e "${YELLOW}참고: DNS 전파에 몇 분 걸릴 수 있습니다${NC}"