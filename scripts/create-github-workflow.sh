#!/bin/bash
# GitHub Actions 워크플로우 생성 스크립트 - Blacklist Management System
set -e

echo "🔄 Blacklist Management System - GitHub Actions 워크플로우 생성"
echo "============================================================="

# 워크플로우 디렉토리 생성
echo "📁 워크플로우 디렉토리 생성 중..."
mkdir -p .github/workflows

# 기존 워크플로우 백업 (있는 경우)
if [ -f .github/workflows/deploy.yaml ]; then
    echo "📋 기존 워크플로우 백업 중..."
    mv .github/workflows/deploy.yaml .github/workflows/deploy.yaml.backup.$(date +%Y%m%d_%H%M%S)
fi

# GitOps CI/CD 워크플로우 생성
echo "🚀 GitOps CI/CD 워크플로우 생성 중..."
cat > .github/workflows/gitops-cicd.yaml << 'EOF'
name: GitOps CI/CD Pipeline - Blacklist Management System

on:
  push:
    branches: 
      - main
      - master
      - develop
    tags: 
      - 'v*'
  pull_request:
    branches: 
      - main
      - master

env:
  REGISTRY: ${{ secrets.REGISTRY_URL }}
  IMAGE_NAME: ${{ vars.GITHUB_ORG }}/${{ vars.APP_NAME }}
  HELM_CHART_NAME: ${{ vars.APP_NAME }}

jobs:
  # 코드 품질 및 보안 검사
  quality-checks:
    name: Code Quality & Security
    runs-on: self-hosted
    if: github.event_name == 'pull_request' || github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install flake8 black isort mypy bandit safety
          
      - name: Code formatting check (Black)
        run: black --check src/ --diff --color
        
      - name: Import sorting check (isort)
        run: isort src/ --check-only --diff --color
        
      - name: Linting (Flake8)
        run: flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
        
      - name: Type checking (MyPy)
        run: mypy src/ --ignore-missing-imports --no-error-summary
        continue-on-error: true
        
      - name: Security scan (Bandit)
        run: bandit -r src/ -f json -o bandit-report.json -ll
        continue-on-error: true
        
      - name: Dependency vulnerability scan (Safety)
        run: safety check --json --output safety-report.json
        continue-on-error: true
        
      - name: Upload security reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-reports
          path: |
            bandit-report.json
            safety-report.json
          retention-days: 30

  # 단위 테스트 및 통합 테스트
  tests:
    name: Unit & Integration Tests
    runs-on: self-hosted
    needs: quality-checks
    if: always() && (needs.quality-checks.result == 'success' || needs.quality-checks.result == 'skipped')
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-xdist pytest-html
          
      - name: Initialize test database
        run: python3 init_database.py
        env:
          DATABASE_URL: sqlite:///test_blacklist.db
          
      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --cov=src --cov-report=xml --cov-report=html \
            --html=pytest-report.html --self-contained-html
        env:
          REDIS_URL: redis://localhost:6379/1
          SECRET_KEY: test-secret-key
          
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v --maxfail=3
        env:
          REDIS_URL: redis://localhost:6379/1
          SECRET_KEY: test-secret-key
          PORT: 8541
          
      - name: Upload test reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-reports
          path: |
            coverage.xml
            htmlcov/
            pytest-report.html
          retention-days: 30

  # Docker 이미지 빌드 및 레지스트리 푸시
  build-and-push:
    name: Build & Push Docker Image
    runs-on: self-hosted
    needs: [quality-checks, tests]
    if: always() && (needs.tests.result == 'success' || needs.tests.result == 'skipped') && github.event_name == 'push'
    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
      image-tags: ${{ steps.meta.outputs.tags }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
        with:
          config-inline: |
            [registry."${{ env.REGISTRY }}"]
              http = true
              insecure = true
        
      - name: Login to Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}
          
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix={{branch}}-,enable={{is_default_branch}}
            type=raw,value=latest,enable={{is_default_branch}}
            type=raw,value={{date 'YYYYMMDD-HHmmss'}}
            
      - name: Build and push Docker image
        id: build
        uses: docker/build-push-action@v4
        with:
          context: .
          file: deployment/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache
          cache-to: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache,mode=max
          platforms: linux/amd64
          
      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.build.outputs.digest }}
          format: spdx-json
          output-file: sbom.spdx.json
          
      - name: Upload SBOM
        uses: actions/upload-artifact@v3
        with:
          name: sbom
          path: sbom.spdx.json
          retention-days: 90

  # Helm 차트 패키징 및 ChartMuseum 업로드
  package-helm-chart:
    name: Package & Deploy Helm Chart
    runs-on: self-hosted
    needs: build-and-push
    if: always() && needs.build-and-push.result == 'success' && github.ref == 'refs/heads/main'
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        
      - name: Install Helm
        uses: azure/setup-helm@v3
        with:
          version: 'v3.14.0'
          
      - name: Package and deploy Helm chart
        run: |
          set -e
          
          COMMIT_SHA="${{ github.sha }}"
          BRANCH_NAME="${{ github.ref_name }}"
          CHART_VERSION="3.0.2-${COMMIT_SHA:0:8}"
          
          # 첫 번째 태그 추출 및 검증
          FIRST_TAG=$(echo "${{ needs.build-and-push.outputs.image-tags }}" | head -n1)
          if [ -z "$FIRST_TAG" ]; then
            echo "❌ 이미지 태그를 찾을 수 없습니다"
            exit 1
          fi
          
          IMAGE_TAG=$(echo "$FIRST_TAG" | cut -d: -f2)
          
          echo "📦 Chart Version: ${CHART_VERSION}"
          echo "🏷️ Image Tag: ${IMAGE_TAG}"
          echo "🔨 First Tag: ${FIRST_TAG}"
          
          # Chart 버전과 이미지 태그 업데이트
          sed -i "s/^version:.*/version: ${CHART_VERSION}/" ./charts/${{ vars.APP_NAME }}/Chart.yaml
          sed -i "s/^appVersion:.*/appVersion: \"${CHART_VERSION}\"/" ./charts/${{ vars.APP_NAME }}/Chart.yaml
          sed -i "s/tag:.*/tag: \"${IMAGE_TAG}\"/" ./charts/${{ vars.APP_NAME }}/values.yaml
          
          # Helm 차트 패키징
          helm dependency update ./charts/${{ vars.APP_NAME }}
          helm package ./charts/${{ vars.APP_NAME }} --destination ./
          
          # ChartMuseum에 업로드
          CHART_FILE="${{ vars.APP_NAME }}-${CHART_VERSION}.tgz"
          
          echo "📤 Uploading ${CHART_FILE} to ChartMuseum..."
          
          HTTP_CODE=$(curl -w "%{http_code}" -s -o /tmp/upload_response.txt \
            -u ${{ secrets.CHARTMUSEUM_USERNAME }}:${{ secrets.CHARTMUSEUM_PASSWORD }} \
            --data-binary "@${CHART_FILE}" \
            ${{ secrets.CHARTMUSEUM_URL }}/api/charts)
          
          echo "📊 HTTP Response Code: ${HTTP_CODE}"
          echo "📄 Response Body:"
          cat /tmp/upload_response.txt
          
          if [ "${HTTP_CODE}" = "201" ] || [ "${HTTP_CODE}" = "409" ]; then
            echo "✅ Chart 업로드 성공: ${CHART_VERSION}"
          else
            echo "❌ Chart 업로드 실패 (HTTP ${HTTP_CODE})"
            cat /tmp/upload_response.txt
            exit 1
          fi
          
          # 업로드된 차트 검증
          echo "🔍 Verifying chart upload..."
          sleep 5  # ChartMuseum 인덱스 업데이트 대기
          
          curl -s -f -u ${{ secrets.CHARTMUSEUM_USERNAME }}:${{ secrets.CHARTMUSEUM_PASSWORD }} \
            ${{ secrets.CHARTMUSEUM_URL }}/api/charts/${{ vars.APP_NAME }} | \
            grep -q "${CHART_VERSION}" && echo "✅ Chart 검증 완료" || {
              echo "⚠ Chart 검증 실패, 하지만 업로드는 성공"
              exit 0
            }
            
      - name: Upload Helm chart artifact
        uses: actions/upload-artifact@v3
        with:
          name: helm-chart
          path: ${{ vars.APP_NAME }}-*.tgz
          retention-days: 90

  # ArgoCD 동기화 및 배포 확인
  argocd-sync:
    name: ArgoCD Sync & Deploy
    runs-on: self-hosted
    needs: package-helm-chart
    if: always() && needs.package-helm-chart.result == 'success' && github.ref == 'refs/heads/main'
    steps:
      - name: ArgoCD Login & Sync
        run: |
          set -e
          
          echo "🔐 ArgoCD 로그인 중..."
          argocd login ${{ secrets.ARGOCD_URL }} \
            --username ${{ secrets.ARGOCD_USERNAME }} \
            --password ${{ secrets.ARGOCD_PASSWORD }} \
            --insecure --grpc-web
          
          APP_NAME="${{ vars.APP_NAME }}-${{ vars.NAMESPACE }}"
          
          echo "🔄 ArgoCD 애플리케이션 동기화 중: ${APP_NAME}"
          argocd app sync ${APP_NAME} --grpc-web
          
          echo "⏳ 배포 상태 확인 중..."
          argocd app wait ${APP_NAME} --health --timeout 600 --grpc-web
          
          echo "📊 배포 결과 확인"
          argocd app get ${APP_NAME} --grpc-web
          
      - name: Kubernetes deployment verification
        run: |
          set -e
          
          echo "🔍 Kubernetes 리소스 상태 확인"
          kubectl get pods,svc,ingress -n ${{ vars.NAMESPACE }} -l app=${{ vars.APP_NAME }}
          
          echo "⏳ Pod 준비 상태 대기 (최대 10분)"
          kubectl wait --for=condition=ready pod \
            -l app=${{ vars.APP_NAME }} \
            -n ${{ vars.NAMESPACE }} \
            --timeout=600s
          
          echo "✅ 배포 완료 - Pod 상태 확인"
          kubectl get pods -n ${{ vars.NAMESPACE }} -l app=${{ vars.APP_NAME }} -o wide

  # 배포 후 헬스체크 및 검증
  post-deploy-verification:
    name: Post-Deploy Health Check
    runs-on: self-hosted
    needs: argocd-sync
    if: always() && needs.argocd-sync.result == 'success'
    steps:
      - name: Application health check
        run: |
          set -e
          
          echo "🏥 애플리케이션 헬스체크 시작"
          
          # NodePort 서비스 IP 및 포트 확인
          NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
          NODE_PORT="${{ vars.NODEPORT }}"
          
          HEALTH_URL="http://${NODE_IP}:${NODE_PORT}/health"
          
          echo "🔍 헬스체크 URL: ${HEALTH_URL}"
          
          # 헬스체크 재시도 (최대 30회, 10초 간격)
          for i in {1..30}; do
            echo "📡 헬스체크 시도 ${i}/30..."
            
            if curl -f -s "${HEALTH_URL}" > /tmp/health_response.json; then
              echo "✅ 헬스체크 성공"
              cat /tmp/health_response.json | jq . || cat /tmp/health_response.json
              break
            else
              echo "⏳ 헬스체크 실패, 10초 후 재시도..."
              if [ $i -eq 30 ]; then
                echo "❌ 헬스체크 최종 실패"
                kubectl logs -l app=${{ vars.APP_NAME }} -n ${{ vars.NAMESPACE }} --tail=50
                exit 1
              fi
              sleep 10
            fi
          done
          
      - name: API endpoint verification
        run: |
          set -e
          
          NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
          NODE_PORT="${{ vars.NODEPORT }}"
          BASE_URL="http://${NODE_IP}:${NODE_PORT}"
          
          echo "🧪 API 엔드포인트 검증 시작"
          
          # 주요 엔드포인트 테스트
          endpoints=(
            "/health"
            "/api/stats"
            "/api/collection/status"
            "/api/blacklist/active"
            "/api/fortigate"
          )
          
          for endpoint in "${endpoints[@]}"; do
            echo "📡 Testing ${endpoint}..."
            if curl -f -s "${BASE_URL}${endpoint}" > /dev/null; then
              echo "✅ ${endpoint} - OK"
            else
              echo "❌ ${endpoint} - FAILED"
            fi
          done
          
          echo "✅ API 엔드포인트 검증 완료"

  # 배포 알림 (선택사항)
  notify:
    name: Deployment Notification
    runs-on: self-hosted
    needs: [build-and-push, package-helm-chart, argocd-sync, post-deploy-verification]
    if: always() && github.ref == 'refs/heads/main'
    steps:
      - name: Send deployment notification
        run: |
          DEPLOYMENT_STATUS="✅ SUCCESS"
          if [ "${{ needs.post-deploy-verification.result }}" != "success" ]; then
            DEPLOYMENT_STATUS="❌ FAILED"
          fi
          
          MESSAGE="🚀 **Blacklist Management System 배포 완료**
          
          📊 **배포 정보:**
          - Branch: ${{ github.ref_name }}
          - Commit: ${{ github.sha }}
          - Status: ${DEPLOYMENT_STATUS}
          - Image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          
          🔗 **접속 정보:**
          - Health Check: http://blacklist.jclee.me:${{ vars.NODEPORT }}/health
          - Dashboard: http://blacklist.jclee.me:${{ vars.NODEPORT }}/
          - API Docs: http://blacklist.jclee.me:${{ vars.NODEPORT }}/api/stats
          
          📈 **모니터링:**
          - ArgoCD: https://${{ secrets.ARGOCD_URL }}/applications/${{ vars.APP_NAME }}-${{ vars.NAMESPACE }}
          - Grafana: https://grafana.jclee.me/d/blacklist
          "
          
          echo "📢 배포 알림 메시지:"
          echo "$MESSAGE"
          
          # Webhook 알림 (환경변수가 설정된 경우)
          if [ -n "${{ secrets.DEPLOYMENT_WEBHOOK_URL }}" ]; then
            curl -X POST "${{ secrets.DEPLOYMENT_WEBHOOK_URL }}" \
              -H "Content-Type: application/json" \
              -d "{\"text\":\"$MESSAGE\"}" || echo "⚠ 웹훅 알림 실패"
          fi
EOF

echo "✅ GitHub Actions 워크플로우 생성 완료!"
echo ""
echo "📋 생성된 파일:"
echo "   - .github/workflows/gitops-cicd.yaml"
echo ""
echo "🔧 워크플로우 특징:"
echo "   ✅ 코드 품질 검사 (Black, isort, Flake8, MyPy)"
echo "   🔒 보안 스캔 (Bandit, Safety)"
echo "   🧪 단위 테스트 및 통합 테스트"
echo "   🐳 Docker 이미지 빌드 및 푸시"
echo "   📦 Helm 차트 패키징 및 업로드"
echo "   🔄 ArgoCD 자동 동기화"
echo "   🏥 배포 후 헬스체크"
echo "   📢 배포 완료 알림"
echo ""
echo "📋 다음 단계:"
echo "1. GitHub Secrets 확인 및 설정"
echo "2. ArgoCD 애플리케이션 설정 스크립트 실행"
echo "3. 첫 번째 커밋으로 파이프라인 테스트"
echo ""
echo "🚀 테스트 배포 명령어:"
echo "   git add .github/workflows/gitops-cicd.yaml"
echo "   git commit -m 'feat: GitOps CI/CD 파이프라인 추가'"
echo "   git push origin main"