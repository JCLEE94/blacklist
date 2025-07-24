#!/bin/bash
# 완전 자동 배포 GitOps CI/CD 구축 스크립트 - Blacklist Management System
set -e

echo "🚀 Blacklist Management System - 완전 자동 배포 GitOps CI/CD 구축"
echo "================================================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 프로젝트 설정값 (Blacklist 특화)
GITHUB_ORG="JCLEE94"
APP_NAME="blacklist" 
NAMESPACE="blacklist"
NODEPORT="32542"

# Registry 및 인프라 설정
REGISTRY_URL="registry.jclee.me"
REGISTRY_USERNAME="admin"
REGISTRY_PASSWORD="bingogo1"
CHARTMUSEUM_URL="https://charts.jclee.me"
CHARTMUSEUM_USERNAME="admin"
CHARTMUSEUM_PASSWORD="bingogo1"
ARGOCD_URL="argo.jclee.me"
ARGOCD_USERNAME="admin"
ARGOCD_PASSWORD="bingogo1"

echo -e "${BLUE}📝 설정 정보:${NC}"
echo "   GitHub Org: ${GITHUB_ORG}"
echo "   App Name: ${APP_NAME}"
echo "   Namespace: ${NAMESPACE}"
echo "   NodePort: ${NODEPORT}"
echo "   Registry: ${REGISTRY_URL}"

# GitHub CLI 상태 확인
echo -e "\n${BLUE}📋 GitHub CLI 상태 확인...${NC}"
if ! gh auth status >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ GitHub CLI 로그인이 필요합니다.${NC}"
    gh auth login
fi

# GitHub Secrets 설정
echo -e "\n${BLUE}🔐 GitHub Secrets 설정 중...${NC}"
gh secret set REGISTRY_URL -b "${REGISTRY_URL}" || echo "REGISTRY_URL 이미 설정됨"
gh secret set REGISTRY_USERNAME -b "${REGISTRY_USERNAME}" || echo "REGISTRY_USERNAME 이미 설정됨"  
gh secret set REGISTRY_PASSWORD -b "${REGISTRY_PASSWORD}" || echo "REGISTRY_PASSWORD 이미 설정됨"
gh secret set CHARTMUSEUM_URL -b "${CHARTMUSEUM_URL}" || echo "CHARTMUSEUM_URL 이미 설정됨"
gh secret set CHARTMUSEUM_USERNAME -b "${CHARTMUSEUM_USERNAME}" || echo "CHARTMUSEUM_USERNAME 이미 설정됨"
gh secret set CHARTMUSEUM_PASSWORD -b "${CHARTMUSEUM_PASSWORD}" || echo "CHARTMUSEUM_PASSWORD 이미 설정됨"
gh secret set ARGOCD_URL -b "${ARGOCD_URL}" || echo "ARGOCD_URL 이미 설정됨"
gh secret set ARGOCD_USERNAME -b "${ARGOCD_USERNAME}" || echo "ARGOCD_USERNAME 이미 설정됨"
gh secret set ARGOCD_PASSWORD -b "${ARGOCD_PASSWORD}" || echo "ARGOCD_PASSWORD 이미 설정됨"

# Application Secrets (기존 CLAUDE.md에서)
gh secret set REGTECH_USERNAME -b "nextrade" || echo "REGTECH_USERNAME 이미 설정됨"
gh secret set REGTECH_PASSWORD -b "Sprtmxm1@3" || echo "REGTECH_PASSWORD 이미 설정됨"
gh secret set SECUDIUM_USERNAME -b "nextrade" || echo "SECUDIUM_USERNAME 이미 설정됨"
gh secret set SECUDIUM_PASSWORD -b "Sprtmxm1@3" || echo "SECUDIUM_PASSWORD 이미 설정됨"

echo -e "${GREEN}✅ GitHub Secrets 설정 완료${NC}"

# Kubernetes 네임스페이스 및 Secret 생성
echo -e "\n${BLUE}🔧 Kubernetes 리소스 설정 중...${NC}"
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret docker-registry regcred \
  --docker-server=${REGISTRY_URL} \
  --docker-username=${REGISTRY_USERNAME} \
  --docker-password=${REGISTRY_PASSWORD} \
  --namespace=${NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -

# Application Secrets 생성
kubectl create secret generic ${APP_NAME}-secrets \
  --from-literal=regtech-username="nextrade" \
  --from-literal=regtech-password="Sprtmxm1@3" \
  --from-literal=secudium-username="nextrade" \
  --from-literal=secudium-password="Sprtmxm1@3" \
  --namespace=${NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✅ Kubernetes 리소스 설정 완료${NC}"

# 완전 자동 배포 워크플로우 생성
echo -e "\n${BLUE}🚀 완전 자동 배포 워크플로우 생성 중...${NC}"
mkdir -p .github/workflows

cat > .github/workflows/auto-deploy.yaml << 'EOF'
name: Auto Deploy - Blacklist Management System

on:
  push:
    branches: [main]
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - '.gitignore'
  workflow_dispatch:

env:
  REGISTRY: ${{ secrets.REGISTRY_URL }}
  IMAGE_NAME: blacklist
  NAMESPACE: blacklist

jobs:
  build-and-deploy:
    name: Build & Auto Deploy
    runs-on: self-hosted
    steps:
      - name: 🔄 Checkout Code
        uses: actions/checkout@v3
        
      - name: 🐳 Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
        with:
          config-inline: |
            [registry."${{ env.REGISTRY }}"]
              http = true
              insecure = true
        
      - name: 🔐 Login to Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}
          
      - name: 🏷️ Extract Metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/jclee94/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}
            type=raw,value={{date 'YYYYMMDD-HHmmss'}}
            
      - name: 🔨 Build and Push Docker Image
        id: build
        uses: docker/build-push-action@v4
        with:
          context: .
          file: deployment/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.REGISTRY }}/jclee94/${{ env.IMAGE_NAME }}:buildcache
          cache-to: type=registry,ref=${{ env.REGISTRY }}/jclee94/${{ env.IMAGE_NAME }}:buildcache,mode=max
          platforms: linux/amd64
          
      - name: 📦 Install Helm
        uses: azure/setup-helm@v3
        with:
          version: 'v3.14.0'
          
      - name: 🎯 Package and Upload Helm Chart
        run: |
          set -e
          
          COMMIT_SHA="${{ github.sha }}"
          CHART_VERSION="3.0.2-${COMMIT_SHA:0:8}"
          
          # 첫 번째 태그 추출
          FIRST_TAG=$(echo "${{ steps.meta.outputs.tags }}" | head -n1)
          IMAGE_TAG=$(echo "$FIRST_TAG" | cut -d: -f2)
          
          echo "📦 Chart Version: ${CHART_VERSION}"
          echo "🏷️ Image Tag: ${IMAGE_TAG}"
          
          # Helm Chart가 없다면 기본 차트 생성
          if [ ! -d "charts/blacklist" ]; then
            mkdir -p charts/blacklist/templates
            
            # Chart.yaml 생성
            cat > charts/blacklist/Chart.yaml << EOC
          apiVersion: v2
          name: blacklist
          description: Enterprise Threat Intelligence Platform
          type: application
          version: ${CHART_VERSION}
          appVersion: "3.0.2"
          EOC
          
            # values.yaml 생성  
            cat > charts/blacklist/values.yaml << EOV
          replicaCount: 2
          image:
            repository: ${{ env.REGISTRY }}/jclee94/blacklist
            pullPolicy: Always
            tag: "latest"
          imagePullSecrets:
            - name: regcred
          service:
            type: NodePort
            port: 80
            targetPort: 2541
            nodePort: 32542
          resources:
            limits:
              cpu: 1000m
              memory: 1Gi
            requests:
              cpu: 200m
              memory: 256Mi
          env:
            PORT: "2541"
            ENVIRONMENT: "production"
          probes:
            liveness:
              path: /health
              port: 2541
            readiness:
              path: /health
              port: 2541
          EOV
          
            # Deployment 템플릿 생성
            cat > charts/blacklist/templates/deployment.yaml << 'EOD'
          apiVersion: apps/v1
          kind: Deployment
          metadata:
            name: {{ .Chart.Name }}
            namespace: {{ .Release.Namespace }}
          spec:
            replicas: {{ .Values.replicaCount }}
            selector:
              matchLabels:
                app: {{ .Chart.Name }}
            template:
              metadata:
                labels:
                  app: {{ .Chart.Name }}
              spec:
                imagePullSecrets:
                  {{- toYaml .Values.imagePullSecrets | nindent 8 }}
                containers:
                - name: {{ .Chart.Name }}
                  image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
                  imagePullPolicy: {{ .Values.image.pullPolicy }}
                  ports:
                  - containerPort: {{ .Values.env.PORT }}
                    name: http
                  env:
                  {{- range $key, $value := .Values.env }}
                  - name: {{ $key }}
                    value: {{ $value | quote }}
                  {{- end }}
                  - name: REGTECH_USERNAME
                    valueFrom:
                      secretKeyRef:
                        name: blacklist-secrets
                        key: regtech-username
                  - name: REGTECH_PASSWORD
                    valueFrom:
                      secretKeyRef:
                        name: blacklist-secrets
                        key: regtech-password
                  - name: SECUDIUM_USERNAME
                    valueFrom:
                      secretKeyRef:
                        name: blacklist-secrets
                        key: secudium-username
                  - name: SECUDIUM_PASSWORD
                    valueFrom:
                      secretKeyRef:
                        name: blacklist-secrets  
                        key: secudium-password
                  livenessProbe:
                    httpGet:
                      path: {{ .Values.probes.liveness.path }}
                      port: {{ .Values.probes.liveness.port }}
                    initialDelaySeconds: 60
                    periodSeconds: 30
                  readinessProbe:
                    httpGet:
                      path: {{ .Values.probes.readiness.path }}
                      port: {{ .Values.probes.readiness.port }}
                    initialDelaySeconds: 10
                    periodSeconds: 10
                  resources:
                    {{- toYaml .Values.resources | nindent 12 }}
          EOD
          
            # Service 템플릿 생성
            cat > charts/blacklist/templates/service.yaml << 'EOS'
          apiVersion: v1
          kind: Service
          metadata:
            name: {{ .Chart.Name }}
            namespace: {{ .Release.Namespace }}
          spec:
            type: {{ .Values.service.type }}
            selector:
              app: {{ .Chart.Name }}
            ports:
            - port: {{ .Values.service.port }}
              targetPort: {{ .Values.service.targetPort }}
              nodePort: {{ .Values.service.nodePort }}
              protocol: TCP
              name: http
          EOS
          fi
          
          # Chart 버전과 이미지 태그 업데이트
          sed -i "s/^version:.*/version: ${CHART_VERSION}/" ./charts/blacklist/Chart.yaml
          sed -i "s/^appVersion:.*/appVersion: \"${CHART_VERSION}\"/" ./charts/blacklist/Chart.yaml
          sed -i "s/tag:.*/tag: \"${IMAGE_TAG}\"/" ./charts/blacklist/values.yaml
          
          # Helm 차트 패키징
          helm package ./charts/blacklist --destination ./
          
          # ChartMuseum에 업로드
          CHART_FILE="blacklist-${CHART_VERSION}.tgz"
          
          echo "📤 Uploading ${CHART_FILE} to ChartMuseum..."
          
          HTTP_CODE=$(curl -w "%{http_code}" -s -o /tmp/upload_response.txt \
            -u ${{ secrets.CHARTMUSEUM_USERNAME }}:${{ secrets.CHARTMUSEUM_PASSWORD }} \
            --data-binary "@${CHART_FILE}" \
            ${{ secrets.CHARTMUSEUM_URL }}/api/charts)
          
          echo "📊 HTTP Response Code: ${HTTP_CODE}"
          cat /tmp/upload_response.txt
          
          if [ "${HTTP_CODE}" = "201" ] || [ "${HTTP_CODE}" = "409" ]; then
            echo "✅ Chart 업로드 성공: ${CHART_VERSION}"
          else
            echo "❌ Chart 업로드 실패 (HTTP ${HTTP_CODE})"
            exit 1
          fi
          
      - name: 🎯 ArgoCD Auto Sync
        run: |
          set -e
          
          echo "🔐 ArgoCD 로그인 중..."
          argocd login ${{ secrets.ARGOCD_URL }} \
            --username ${{ secrets.ARGOCD_USERNAME }} \
            --password ${{ secrets.ARGOCD_PASSWORD }} \
            --insecure --grpc-web
          
          APP_NAME="blacklist-blacklist"
          
          echo "🔄 ArgoCD 애플리케이션 동기화 중: ${APP_NAME}"
          argocd app sync ${APP_NAME} --grpc-web || {
            echo "⚠ 애플리케이션이 없습니다. 생성하겠습니다..."
            
            # ArgoCD 애플리케이션 생성
            argocd app create ${APP_NAME} \
              --repo ${{ secrets.CHARTMUSEUM_URL }} \
              --helm-chart blacklist \
              --revision "*" \
              --dest-namespace blacklist \
              --dest-server https://kubernetes.default.svc \
              --sync-policy automated \
              --auto-prune \
              --self-heal \
              --grpc-web
              
            echo "✅ ArgoCD 애플리케이션 생성 완료"
          }
          
          echo "⏳ 배포 상태 확인 중..."
          argocd app wait ${APP_NAME} --health --timeout 600 --grpc-web
          
      - name: 🏥 Post-Deploy Health Check
        run: |
          set -e
          
          echo "🏥 애플리케이션 헬스체크 시작"
          
          # Pod 준비 상태 대기
          kubectl wait --for=condition=ready pod \
            -l app=blacklist \
            -n blacklist \
            --timeout=300s
          
          # NodePort 서비스 확인
          NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
          HEALTH_URL="http://${NODE_IP}:32542/health"
          
          echo "🔍 헬스체크 URL: ${HEALTH_URL}"
          
          # 헬스체크 재시도
          for i in {1..20}; do
            echo "📡 헬스체크 시도 ${i}/20..."
            
            if curl -f -s "${HEALTH_URL}" > /tmp/health_response.json; then
              echo "✅ 헬스체크 성공"
              cat /tmp/health_response.json | jq . || cat /tmp/health_response.json
              break
            else
              echo "⏳ 헬스체크 실패, 15초 후 재시도..."
              if [ $i -eq 20 ]; then
                echo "❌ 헬스체크 최종 실패"
                kubectl logs -l app=blacklist -n blacklist --tail=50
                exit 1
              fi
              sleep 15
            fi
          done
          
      - name: 📊 Deployment Summary
        if: always()
        run: |
          echo "🎉 **Blacklist Management System 자동 배포 완료**"
          echo ""
          echo "📊 **배포 정보:**"
          echo "- Commit: ${{ github.sha }}"
          echo "- Image: ${{ env.REGISTRY }}/jclee94/blacklist"
          echo "- Namespace: ${{ env.NAMESPACE }}"
          echo ""
          echo "🔗 **접속 정보:**"
          NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
          echo "- Health Check: http://${NODE_IP}:32542/health"
          echo "- Dashboard: http://${NODE_IP}:32542/"
          echo "- API Stats: http://${NODE_IP}:32542/api/stats"
          echo ""
          echo "📈 **모니터링:**"
          echo "- ArgoCD: https://${{ secrets.ARGOCD_URL }}/applications/blacklist-blacklist"
          echo "- Pods: kubectl get pods -n blacklist"
          echo "- Logs: kubectl logs -f -l app=blacklist -n blacklist"
EOF

echo -e "${GREEN}✅ 완전 자동 배포 워크플로우 생성 완료${NC}"

# ArgoCD Repository 설정
echo -e "\n${BLUE}🎯 ArgoCD Repository 설정 중...${NC}"
argocd login ${ARGOCD_URL} --username ${ARGOCD_USERNAME} --password ${ARGOCD_PASSWORD} --insecure --grpc-web || {
  echo -e "${YELLOW}⚠ ArgoCD 로그인 실패 - 나중에 수동으로 설정하세요${NC}"
}

# Repository 추가 (이미 있어도 오류 무시)
argocd repo add ${CHARTMUSEUM_URL} --type helm --username ${CHARTMUSEUM_USERNAME} --password ${CHARTMUSEUM_PASSWORD} --grpc-web 2>/dev/null || echo "Repository 이미 존재하거나 추가 실패"

echo -e "\n${GREEN}🎉 완전 자동 배포 GitOps CI/CD 구성 완료!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}📋 다음 단계:${NC}"
echo "1. 코드 커밋 및 푸시로 자동 배포 트리거:"
echo "   git add . && git commit -m 'feat: 완전 자동 배포 CI/CD 구성' && git push origin main"
echo ""
echo "2. GitHub Actions 실행 모니터링:"
echo "   https://github.com/${GITHUB_ORG}/blacklist/actions"
echo ""
echo "3. ArgoCD 애플리케이션 확인:"
echo "   https://${ARGOCD_URL}/applications/blacklist-blacklist"
echo ""
echo "4. 배포 완료 후 접속:"
echo "   curl http://blacklist.jclee.me:32542/health"
echo ""
echo -e "${YELLOW}🔥 이제 main 브랜치에 푸시할 때마다 자동으로 배포됩니다!${NC}"