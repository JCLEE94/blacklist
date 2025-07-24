#!/bin/bash
# ArgoCD 애플리케이션 설정 스크립트 - Blacklist Management System
set -e

echo "🎯 Blacklist Management System - ArgoCD 애플리케이션 설정"
echo "========================================================"

# 설정값
APP_NAME="blacklist"
NAMESPACE="${NAMESPACE:-blacklist}"
GITHUB_ORG="${GITHUB_ORG:-JCLEE94}"
ARGOCD_URL="${ARGOCD_URL:-argo.jclee.me}"
ARGOCD_USERNAME="${ARGOCD_USERNAME:-admin}"
ARGOCD_PASSWORD="${ARGOCD_PASSWORD:-bingogo1}"
CHARTMUSEUM_URL="${CHARTMUSEUM_URL:-https://charts.jclee.me}"
CHARTMUSEUM_USERNAME="${CHARTMUSEUM_USERNAME:-admin}"
CHARTMUSEUM_PASSWORD="${CHARTMUSEUM_PASSWORD:-bingogo1}"

echo "📝 설정 정보:"
echo "   App Name: ${APP_NAME}"
echo "   Namespace: ${NAMESPACE}"
echo "   ArgoCD URL: ${ARGOCD_URL}"
echo "   ChartMuseum URL: ${CHARTMUSEUM_URL}"

# ArgoCD 애플리케이션 매니페스트 생성
echo "📋 ArgoCD 애플리케이션 매니페스트 생성 중..."
mkdir -p argocd/

cat > argocd/application.yaml << EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ${APP_NAME}-${NAMESPACE}
  namespace: argocd
  labels:
    app: ${APP_NAME}
    env: ${NAMESPACE}
    component: threat-intelligence
    managed-by: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
  annotations:
    argocd.argoproj.io/sync-wave: "1"
    argocd.argoproj.io/sync-options: Prune=true,Delete=true
spec:
  project: default
  source:
    repoURL: ${CHARTMUSEUM_URL}
    chart: ${APP_NAME}
    targetRevision: "*"
    helm:
      releaseName: ${APP_NAME}
      valueFiles:
        - values.yaml
      parameters:
        - name: image.tag
          value: "latest"
        - name: replicaCount
          value: "2"
        - name: env.ENVIRONMENT
          value: "production"
      values: |
        # Production overrides
        image:
          pullPolicy: Always
        
        resources:
          limits:
            cpu: 1000m
            memory: 1Gi
          requests:
            cpu: 200m
            memory: 256Mi
        
        # Security context
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          runAsGroup: 1000
          fsGroup: 1000
        
        # High availability
        affinity:
          podAntiAffinity:
            preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                  - key: app
                    operator: In
                    values:
                    - ${APP_NAME}
                topologyKey: kubernetes.io/hostname
        
        # HPA settings
        hpa:
          enabled: true
          minReplicas: 2
          maxReplicas: 6
          targetCPUUtilizationPercentage: 70
          targetMemoryUtilizationPercentage: 80
        
        # Monitoring
        serviceMonitor:
          enabled: false
          namespace: monitoring
  destination:
    server: https://kubernetes.default.svc
    namespace: ${NAMESPACE}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
      - FailOnSharedResource=false
      - RespectIgnoreDifferences=true
    managedNamespaceMetadata:
      labels:
        app: ${APP_NAME}
        managed-by: argocd
        environment: production
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  revisionHistoryLimit: 10
  ignoreDifferences:
    - group: apps
      kind: Deployment
      managedFieldsManagers:
        - kube-controller-manager
    - group: ""
      kind: Service
      managedFieldsManagers:
        - kube-controller-manager
EOF

# ArgoCD Repository 설정 매니페스트 생성
echo "📦 ArgoCD Repository 설정 매니페스트 생성 중..."
cat > argocd/repository.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${APP_NAME}-helm-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: helm
  name: ${APP_NAME}-charts
  url: ${CHARTMUSEUM_URL}
  username: ${CHARTMUSEUM_USERNAME}
  password: ${CHARTMUSEUM_PASSWORD}
  enableOCI: "false"
EOF

# ArgoCD 프로젝트 설정 (선택사항)
echo "🎯 ArgoCD 프로젝트 설정 매니페스트 생성 중..."
cat > argocd/project.yaml << EOF
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: ${APP_NAME}-project
  namespace: argocd
  labels:
    app: ${APP_NAME}
spec:
  description: "Blacklist Management System - Enterprise Threat Intelligence Platform"
  sourceRepos:
    - '${CHARTMUSEUM_URL}'
    - 'https://github.com/${GITHUB_ORG}/${APP_NAME}'
  destinations:
    - namespace: ${NAMESPACE}
      server: https://kubernetes.default.svc
    - namespace: argocd
      server: https://kubernetes.default.svc
  clusterResourceWhitelist:
    - group: ''
      kind: Namespace
    - group: 'rbac.authorization.k8s.io'
      kind: ClusterRole
    - group: 'rbac.authorization.k8s.io'
      kind: ClusterRoleBinding
  namespaceResourceWhitelist:
    - group: ''
      kind: ConfigMap
    - group: ''
      kind: Secret
    - group: ''
      kind: Service
    - group: ''
      kind: PersistentVolumeClaim
    - group: 'apps'
      kind: Deployment
    - group: 'apps'
      kind: ReplicaSet
    - group: 'autoscaling'
      kind: HorizontalPodAutoscaler
    - group: 'networking.k8s.io'
      kind: Ingress
    - group: 'monitoring.coreos.com'
      kind: ServiceMonitor
  roles:
    - name: readonly
      description: "Read-only access to ${APP_NAME} project"
      policies:
        - p, proj:${APP_NAME}-project:readonly, applications, get, ${APP_NAME}-project/*, allow
        - p, proj:${APP_NAME}-project:readonly, applications, sync, ${APP_NAME}-project/*, deny
      groups:
        - ${APP_NAME}-readonly
    - name: admin
      description: "Admin access to ${APP_NAME} project"
      policies:
        - p, proj:${APP_NAME}-project:admin, applications, *, ${APP_NAME}-project/*, allow
        - p, proj:${APP_NAME}-project:admin, repositories, *, *, allow
      groups:
        - ${APP_NAME}-admin
  syncWindows:
    - kind: allow
      schedule: '0 0 * * *'
      duration: 24h
      applications:
        - '${APP_NAME}-*'
      manualSync: true
  orphanedResources:
    warn: true
    ignore:
      - group: ''
        kind: ConfigMap
        name: kube-root-ca.crt
EOF

# Kubernetes namespace 및 secrets 설정 스크립트
echo "🔐 Kubernetes 설정 스크립트 생성 중..."
cat > argocd/setup-k8s-resources.sh << 'EOF'
#!/bin/bash
# Kubernetes 리소스 설정 스크립트
set -e

NAMESPACE="blacklist"
REGISTRY_URL="registry.jclee.me"
REGISTRY_USERNAME="admin"
REGISTRY_PASSWORD="bingogo1"

echo "📦 Namespace 생성 중..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

echo "🔐 Registry Secret 생성 중..."
kubectl create secret docker-registry regcred \
  --docker-server=${REGISTRY_URL} \
  --docker-username=${REGISTRY_USERNAME} \
  --docker-password=${REGISTRY_PASSWORD} \
  --namespace=${NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -

echo "🔑 Application Secrets 생성 중..."
kubectl create secret generic blacklist-secrets \
  --from-literal=regtech-username="nextrade" \
  --from-literal=regtech-password="Sprtmxm1@3" \
  --from-literal=secudium-username="nextrade" \
  --from-literal=secudium-password="Sprtmxm1@3" \
  --namespace=${NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Kubernetes 리소스 설정 완료"
EOF

chmod +x argocd/setup-k8s-resources.sh

# ArgoCD CLI 설정 및 배포 스크립트
echo "🚀 ArgoCD 배포 스크립트 생성 중..."
cat > argocd/deploy-argocd-app.sh << EOF
#!/bin/bash
# ArgoCD 애플리케이션 배포 스크립트
set -e

echo "🎯 ArgoCD 애플리케이션 배포 시작"

# ArgoCD 로그인
echo "🔐 ArgoCD 로그인 중..."
argocd login ${ARGOCD_URL} \\
  --username ${ARGOCD_USERNAME} \\
  --password ${ARGOCD_PASSWORD} \\
  --insecure --grpc-web

# Repository 등록 확인 및 추가
echo "📦 Repository 등록 확인 중..."
if ! argocd repo list --grpc-web | grep -q "${CHARTMUSEUM_URL}"; then
  echo "📤 Repository 등록 중..."
  argocd repo add ${CHARTMUSEUM_URL} \\
    --type helm \\
    --username ${CHARTMUSEUM_USERNAME} \\
    --password ${CHARTMUSEUM_PASSWORD} \\
    --grpc-web
else
  echo "✅ Repository 이미 등록됨"
fi

# Kubernetes 리소스 설정
echo "🔧 Kubernetes 리소스 설정 중..."
./argocd/setup-k8s-resources.sh

# ArgoCD 애플리케이션 생성
echo "🚀 ArgoCD 애플리케이션 생성 중..."
kubectl apply -f argocd/repository.yaml
kubectl apply -f argocd/application.yaml

# 애플리케이션 동기화 대기
APP_NAME="${APP_NAME}-${NAMESPACE}"
echo "⏳ 애플리케이션 동기화 대기 중: \${APP_NAME}"
argocd app wait \${APP_NAME} --sync --grpc-web

# 첫 동기화 실행
echo "🔄 첫 동기화 실행 중..."
argocd app sync \${APP_NAME} --grpc-web

# 헬스체크 대기
echo "🏥 헬스체크 대기 중..."
argocd app wait \${APP_NAME} --health --timeout 600 --grpc-web

# 결과 확인
echo "📊 배포 결과 확인"
argocd app get \${APP_NAME} --grpc-web
kubectl get pods,svc -n ${NAMESPACE} -l app=${APP_NAME}

echo "✅ ArgoCD 애플리케이션 배포 완료!"
echo ""
echo "🔗 접속 정보:"
echo "   ArgoCD UI: https://${ARGOCD_URL}/applications/\${APP_NAME}"
echo "   Health Check: http://blacklist.jclee.me:32542/health"
echo "   Dashboard: http://blacklist.jclee.me:32542/"
EOF

chmod +x argocd/deploy-argocd-app.sh

# ArgoCD Image Updater 설정
echo "🔄 ArgoCD Image Updater 설정 생성 중..."
cat > argocd/image-updater-config.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-image-updater-config
  namespace: argocd
  labels:
    app.kubernetes.io/name: argocd-image-updater
    app.kubernetes.io/part-of: argocd
data:
  registries.conf: |
    registries:
      - name: registry.jclee.me
        api_url: http://registry.jclee.me:5000
        ping: true
        insecure: true
        credentials: secret:argocd/registry-creds#username,secret:argocd/registry-creds#password
        default: true
  log.level: debug
  applications: |
    ${APP_NAME}-${NAMESPACE}:
      image-list:
        - registry.jclee.me/${GITHUB_ORG}/${APP_NAME}
      update-strategy: latest
      write-back-method: argocd
      ignore-tags:
        - latest
        - buildcache
      platforms:
        - linux/amd64
---
apiVersion: v1
kind: Secret
metadata:
  name: registry-creds
  namespace: argocd
type: Opaque
stringData:
  username: ${CHARTMUSEUM_USERNAME}
  password: ${CHARTMUSEUM_PASSWORD}
EOF

# ArgoCD Application Annotations 업데이트 (Image Updater를 위한)
echo "🏷️ ArgoCD 애플리케이션 어노테이션 업데이트 중..."
cat > argocd/application-with-image-updater.yaml << EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ${APP_NAME}-${NAMESPACE}
  namespace: argocd
  labels:
    app: ${APP_NAME}
    env: ${NAMESPACE}
    component: threat-intelligence
    managed-by: argocd
  annotations:
    # ArgoCD Image Updater 설정
    argocd-image-updater.argoproj.io/image-list: ${APP_NAME}=registry.jclee.me/${GITHUB_ORG}/${APP_NAME}
    argocd-image-updater.argoproj.io/update-strategy: latest
    argocd-image-updater.argoproj.io/write-back-method: argocd
    argocd-image-updater.argoproj.io/ignore-tags: latest,buildcache
    argocd-image-updater.argoproj.io/platforms: linux/amd64
    # ArgoCD 동기화 설정
    argocd.argoproj.io/sync-wave: "1"
    argocd.argoproj.io/sync-options: Prune=true,Delete=true,ServerSideApply=true
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: ${CHARTMUSEUM_URL}
    chart: ${APP_NAME}
    targetRevision: "*"
    helm:
      releaseName: ${APP_NAME}
      valueFiles:
        - values.yaml
      parameters:
        - name: image.tag
          value: "latest"
        - name: replicaCount
          value: "2"
        - name: env.ENVIRONMENT
          value: "production"
  destination:
    server: https://kubernetes.default.svc
    namespace: ${NAMESPACE}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
      - FailOnSharedResource=false
      - RespectIgnoreDifferences=true
    managedNamespaceMetadata:
      labels:
        app: ${APP_NAME}
        managed-by: argocd
        environment: production
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  revisionHistoryLimit: 10
EOF

echo "✅ ArgoCD 설정 파일 생성 완료!"
echo ""
echo "📋 생성된 파일들:"
echo "   - argocd/application.yaml"
echo "   - argocd/repository.yaml"
echo "   - argocd/project.yaml"
echo "   - argocd/setup-k8s-resources.sh"
echo "   - argocd/deploy-argocd-app.sh"
echo "   - argocd/image-updater-config.yaml"
echo "   - argocd/application-with-image-updater.yaml"
echo ""
echo "🚀 배포 단계:"
echo "1. 수동 배포: ./argocd/deploy-argocd-app.sh"
echo "2. 또는 kubectl apply로 개별 리소스 적용"
echo "3. ArgoCD UI에서 애플리케이션 상태 확인"
echo ""
echo "🔧 주요 기능:"
echo "   ✅ 자동 동기화 (prune, selfHeal 활성화)"
echo "   🔄 Image Updater 자동 업데이트"
echo "   🏥 헬스체크 및 동기화 재시도"
echo "   📊 프로젝트 기반 권한 관리"
echo "   🔒 Secrets 및 ConfigMap 자동 생성"
echo ""
echo "🌐 접속 정보:"
echo "   ArgoCD UI: https://${ARGOCD_URL}"
echo "   Application: https://${ARGOCD_URL}/applications/${APP_NAME}-${NAMESPACE}"