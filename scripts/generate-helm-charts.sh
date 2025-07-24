#!/bin/bash
# Helm Charts 생성 스크립트 - Blacklist Management System
set -e

echo "📦 Blacklist Management System - Helm Charts 생성"
echo "================================================"

# 프로젝트 설정값
APP_NAME="blacklist"
GITHUB_ORG="${GITHUB_ORG:-JCLEE94}"
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
PROD_PORT="${PROD_PORT:-2541}"
NODEPORT="${NODEPORT:-32542}"

echo "🏗️ Helm Chart 디렉토리 생성 중..."
rm -rf charts/${APP_NAME} || true
mkdir -p charts/${APP_NAME}/templates

# Chart.yaml 생성
echo "📋 Chart.yaml 생성 중..."
cat > charts/${APP_NAME}/Chart.yaml << EOF
apiVersion: v2
name: ${APP_NAME}
description: Enterprise Threat Intelligence Platform - Blacklist Management System
type: application
version: 3.0.2
appVersion: "3.0.2"
keywords:
  - security
  - threat-intelligence
  - blacklist
  - fortigate
  - ip-management
home: https://github.com/${GITHUB_ORG}/${APP_NAME}
sources:
  - https://github.com/${GITHUB_ORG}/${APP_NAME}
maintainers:
  - name: JCLEE94
    email: jclee@example.com
dependencies:
  - name: redis
    version: "17.15.6"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
EOF

# values.yaml 생성
echo "⚙️ values.yaml 생성 중..."
cat > charts/${APP_NAME}/values.yaml << EOF
# Blacklist Management System - Production Values
replicaCount: 2

image:
  repository: ${REGISTRY_URL}/${GITHUB_ORG}/${APP_NAME}
  pullPolicy: Always
  tag: "latest"

imagePullSecrets:
  - name: regcred

service:
  type: NodePort
  port: 80
  targetPort: ${PROD_PORT}
  nodePort: ${NODEPORT}

# Resource configuration for enterprise workload
resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 200m
    memory: 256Mi

# High availability configuration
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

# Application configuration
env:
  PORT: "${PROD_PORT}"
  SECRET_KEY: "your-production-secret-key-change-this"
  REDIS_URL: "redis://blacklist-redis:6379/0"
  ENVIRONMENT: "production"
  
# Application secrets (will be injected from Kubernetes secrets)
secrets:
  regtechUsername: "nextrade"
  regtechPassword: "change-this-password"
  secudiumUsername: "nextrade"
  secudiumPassword: "change-this-password"
  
# Security context
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000

# Health checks (existing endpoints from CLAUDE.md)
probes:
  liveness:
    path: /health
    port: ${PROD_PORT}
    initialDelaySeconds: 60
    periodSeconds: 30
    timeoutSeconds: 10
    failureThreshold: 3
  readiness:
    path: /health
    port: ${PROD_PORT}
    initialDelaySeconds: 10
    periodSeconds: 10
    timeoutSeconds: 5
    failureThreshold: 3

# Persistent storage for SQLite database
persistence:
  enabled: true
  storageClass: "local-path"
  size: 5Gi
  accessMode: ReadWriteOnce

# Redis dependency (for caching)
redis:
  enabled: true
  auth:
    enabled: false
  replica:
    replicaCount: 1
  master:
    persistence:
      enabled: true
      size: 1Gi
  resources:
    limits:
      cpu: 250m
      memory: 256Mi
    requests:
      cpu: 100m
      memory: 128Mi

# Horizontal Pod Autoscaler
hpa:
  enabled: true
  minReplicas: 2
  maxReplicas: 6
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

# Network Policy (optional)
networkPolicy:
  enabled: false

# Service Monitor for Prometheus (optional)
serviceMonitor:
  enabled: false
  namespace: monitoring
  interval: 30s
  path: /metrics

# Ingress configuration (optional)
ingress:
  enabled: false
  className: "nginx"
  annotations: {}
  hosts:
    - host: blacklist.jclee.me
      paths:
        - path: /
          pathType: Prefix
  tls: []
EOF

# Deployment template
echo "🚀 Deployment template 생성 중..."
cat > charts/${APP_NAME}/templates/deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Chart.Name }}
  namespace: {{ .Release.Namespace }}
  labels:
    app: {{ .Chart.Name }}
    version: {{ .Chart.AppVersion }}
    component: backend
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/version: {{ .Chart.AppVersion }}
    app.kubernetes.io/component: backend
    app.kubernetes.io/part-of: threat-intelligence
    app.kubernetes.io/managed-by: {{ .Release.Service }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Chart.Name }}
      app.kubernetes.io/name: {{ .Chart.Name }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Chart.Name }}
        version: {{ .Chart.AppVersion }}
        component: backend
        app.kubernetes.io/name: {{ .Chart.Name }}
        app.kubernetes.io/instance: {{ .Release.Name }}
        app.kubernetes.io/version: {{ .Chart.AppVersion }}
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
    spec:
      {{- if .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml .Values.imagePullSecrets | nindent 8 }}
      {{- end }}
      {{- if .Values.securityContext }}
      securityContext:
        {{- toYaml .Values.securityContext | nindent 8 }}
      {{- end }}
      {{- if .Values.affinity }}
      affinity:
        {{- toYaml .Values.affinity | nindent 8 }}
      {{- end }}
      initContainers:
      - name: init-db
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        command: ['python3', 'init_database.py']
        env:
        {{- range $key, $value := .Values.env }}
        - name: {{ $key }}
          value: {{ $value | quote }}
        {{- end }}
        volumeMounts:
        - name: blacklist-data
          mountPath: /app/instance
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - containerPort: {{ .Values.env.PORT }}
          name: http
          protocol: TCP
        env:
        {{- range $key, $value := .Values.env }}
        - name: {{ $key }}
          value: {{ $value | quote }}
        {{- end }}
        # Secret environment variables
        - name: REGTECH_USERNAME
          valueFrom:
            secretKeyRef:
              name: {{ .Chart.Name }}-secrets
              key: regtech-username
        - name: REGTECH_PASSWORD
          valueFrom:
            secretKeyRef:
              name: {{ .Chart.Name }}-secrets
              key: regtech-password
        - name: SECUDIUM_USERNAME
          valueFrom:
            secretKeyRef:
              name: {{ .Chart.Name }}-secrets
              key: secudium-username
        - name: SECUDIUM_PASSWORD
          valueFrom:
            secretKeyRef:
              name: {{ .Chart.Name }}-secrets
              key: secudium-password
        {{- if .Values.probes.liveness }}
        livenessProbe:
          httpGet:
            path: {{ .Values.probes.liveness.path }}
            port: {{ .Values.probes.liveness.port }}
          initialDelaySeconds: {{ .Values.probes.liveness.initialDelaySeconds }}
          periodSeconds: {{ .Values.probes.liveness.periodSeconds }}
          timeoutSeconds: {{ .Values.probes.liveness.timeoutSeconds }}
          failureThreshold: {{ .Values.probes.liveness.failureThreshold }}
        {{- end }}
        {{- if .Values.probes.readiness }}
        readinessProbe:
          httpGet:
            path: {{ .Values.probes.readiness.path }}
            port: {{ .Values.probes.readiness.port }}
          initialDelaySeconds: {{ .Values.probes.readiness.initialDelaySeconds }}
          periodSeconds: {{ .Values.probes.readiness.periodSeconds }}
          timeoutSeconds: {{ .Values.probes.readiness.timeoutSeconds }}
          failureThreshold: {{ .Values.probes.readiness.failureThreshold }}
        {{- end }}
        {{- if .Values.resources }}
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
        {{- end }}
        volumeMounts:
        - name: blacklist-data
          mountPath: /app/instance
        - name: config-volume
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: blacklist-data
        {{- if .Values.persistence.enabled }}
        persistentVolumeClaim:
          claimName: {{ .Chart.Name }}-data
        {{- else }}
        emptyDir: {}
        {{- end }}
      - name: config-volume
        configMap:
          name: {{ .Chart.Name }}-config
EOF

# Service template
echo "🌐 Service template 생성 중..."
cat > charts/${APP_NAME}/templates/service.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: {{ .Chart.Name }}
  namespace: {{ .Release.Namespace }}
  labels:
    app: {{ .Chart.Name }}
    component: backend
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/component: backend
spec:
  type: {{ .Values.service.type }}
  selector:
    app: {{ .Chart.Name }}
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
  ports:
  - port: {{ .Values.service.port }}
    targetPort: {{ .Values.service.targetPort }}
    {{- if eq .Values.service.type "NodePort" }}
    nodePort: {{ .Values.service.nodePort }}
    {{- end }}
    protocol: TCP
    name: http
EOF

# ConfigMap template
echo "🔧 ConfigMap template 생성 중..."
cat > charts/${APP_NAME}/templates/configmap.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Chart.Name }}-config
  namespace: {{ .Release.Namespace }}
  labels:
    app: {{ .Chart.Name }}
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
data:
  {{- range $key, $value := .Values.env }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
  # Application specific configuration
  collection.enabled: "true"
  rate.limit.enabled: "true"
  cors.enabled: "true"
  debug: "false"
EOF

# Secret template
echo "🔐 Secret template 생성 중..."
cat > charts/${APP_NAME}/templates/secret.yaml << 'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: {{ .Chart.Name }}-secrets
  namespace: {{ .Release.Namespace }}
  labels:
    app: {{ .Chart.Name }}
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
type: Opaque
data:
  regtech-username: {{ .Values.secrets.regtechUsername | b64enc }}
  regtech-password: {{ .Values.secrets.regtechPassword | b64enc }}
  secudium-username: {{ .Values.secrets.secudiumUsername | b64enc }}
  secudium-password: {{ .Values.secrets.secudiumPassword | b64enc }}
EOF

# PVC template
echo "💾 PVC template 생성 중..."
cat > charts/${APP_NAME}/templates/pvc.yaml << 'EOF'
{{- if .Values.persistence.enabled }}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ .Chart.Name }}-data
  namespace: {{ .Release.Namespace }}
  labels:
    app: {{ .Chart.Name }}
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
spec:
  accessModes:
    - {{ .Values.persistence.accessMode }}
  resources:
    requests:
      storage: {{ .Values.persistence.size }}
  {{- if .Values.persistence.storageClass }}
  storageClassName: {{ .Values.persistence.storageClass }}
  {{- end }}
{{- end }}
EOF

# HPA template
echo "📈 HPA template 생성 중..."
cat > charts/${APP_NAME}/templates/hpa.yaml << 'EOF'
{{- if .Values.hpa.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ .Chart.Name }}
  namespace: {{ .Release.Namespace }}
  labels:
    app: {{ .Chart.Name }}
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ .Chart.Name }}
  minReplicas: {{ .Values.hpa.minReplicas }}
  maxReplicas: {{ .Values.hpa.maxReplicas }}
  metrics:
  {{- if .Values.hpa.targetCPUUtilizationPercentage }}
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ .Values.hpa.targetCPUUtilizationPercentage }}
  {{- end }}
  {{- if .Values.hpa.targetMemoryUtilizationPercentage }}
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: {{ .Values.hpa.targetMemoryUtilizationPercentage }}
  {{- end }}
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
{{- end }}
EOF

# ServiceMonitor template (optional, for Prometheus)
echo "📊 ServiceMonitor template 생성 중..."
cat > charts/${APP_NAME}/templates/servicemonitor.yaml << 'EOF'
{{- if .Values.serviceMonitor.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ .Chart.Name }}
  namespace: {{ .Values.serviceMonitor.namespace }}
  labels:
    app: {{ .Chart.Name }}
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
spec:
  selector:
    matchLabels:
      app: {{ .Chart.Name }}
      app.kubernetes.io/name: {{ .Chart.Name }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  endpoints:
  - port: http
    path: {{ .Values.serviceMonitor.path }}
    interval: {{ .Values.serviceMonitor.interval }}
{{- end }}
EOF

# Ingress template (optional)
echo "🌍 Ingress template 생성 중..."
cat > charts/${APP_NAME}/templates/ingress.yaml << 'EOF'
{{- if .Values.ingress.enabled -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Chart.Name }}
  namespace: {{ .Release.Namespace }}
  labels:
    app: {{ .Chart.Name }}
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.ingress.className }}
  ingressClassName: {{ .Values.ingress.className }}
  {{- end }}
  {{- if .Values.ingress.tls }}
  tls:
    {{- range .Values.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{ . | quote }}
        {{- end }}
      secretName: {{ .secretName }}
    {{- end }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ $.Chart.Name }}
                port:
                  number: {{ $.Values.service.port }}
          {{- end }}
    {{- end }}
{{- end }}
EOF

# NOTES.txt 생성
echo "📝 NOTES.txt 생성 중..."
cat > charts/${APP_NAME}/templates/NOTES.txt << 'EOF'
1. Get the application URL by running these commands:
{{- if .Values.ingress.enabled }}
{{- range $host := .Values.ingress.hosts }}
  {{- range .paths }}
  http{{ if $.Values.ingress.tls }}s{{ end }}://{{ $host.host }}{{ .path }}
  {{- end }}
{{- end }}
{{- else if contains "NodePort" .Values.service.type }}
  export NODE_PORT=$(kubectl get --namespace {{ .Release.Namespace }} -o jsonpath="{.spec.ports[0].nodePort}" services {{ include "blacklist.fullname" . }})
  export NODE_IP=$(kubectl get nodes --namespace {{ .Release.Namespace }} -o jsonpath="{.items[0].status.addresses[0].address}")
  echo http://$NODE_IP:$NODE_PORT
{{- else if contains "LoadBalancer" .Values.service.type }}
     NOTE: It may take a few minutes for the LoadBalancer IP to be available.
           You can watch the status of by running 'kubectl get --namespace {{ .Release.Namespace }} svc -w {{ include "blacklist.fullname" . }}'
  export SERVICE_IP=$(kubectl get svc --namespace {{ .Release.Namespace }} {{ include "blacklist.fullname" . }} --template "{{"{{ range (index .status.loadBalancer.ingress 0) }}{{.}}{{ end }}"}}")
  echo http://$SERVICE_IP:{{ .Values.service.port }}
{{- else if contains "ClusterIP" .Values.service.type }}
  export POD_NAME=$(kubectl get pods --namespace {{ .Release.Namespace }} -l "app.kubernetes.io/name={{ include "blacklist.name" . }},app.kubernetes.io/instance={{ .Release.Name }}" -o jsonpath="{.items[0].metadata.name}")
  export CONTAINER_PORT=$(kubectl get pod --namespace {{ .Release.Namespace }} $POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
  echo "Visit http://127.0.0.1:8080 to use your application"
  kubectl --namespace {{ .Release.Namespace }} port-forward $POD_NAME 8080:$CONTAINER_PORT
{{- end }}

2. Check the status of your deployment:
   kubectl get pods -n {{ .Release.Namespace }} -l app={{ .Chart.Name }}

3. View application logs:
   kubectl logs -f deployment/{{ .Chart.Name }} -n {{ .Release.Namespace }}

4. Access the health endpoint:
   curl http://your-service-url/health

5. Check collection status:
   curl http://your-service-url/api/collection/status
EOF

# Helper templates
echo "🔧 Helper templates 생성 중..."
cat > charts/${APP_NAME}/templates/_helpers.tpl << 'EOF'
{{/*
Expand the name of the chart.
*/}}
{{- define "blacklist.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "blacklist.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "blacklist.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "blacklist.labels" -}}
helm.sh/chart: {{ include "blacklist.chart" . }}
{{ include "blacklist.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "blacklist.selectorLabels" -}}
app.kubernetes.io/name: {{ include "blacklist.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
EOF

echo "✅ Helm Charts 생성 완료!"
echo ""
echo "📋 생성된 파일들:"
echo "   - charts/${APP_NAME}/Chart.yaml"
echo "   - charts/${APP_NAME}/values.yaml"
echo "   - charts/${APP_NAME}/templates/deployment.yaml"
echo "   - charts/${APP_NAME}/templates/service.yaml"
echo "   - charts/${APP_NAME}/templates/configmap.yaml"
echo "   - charts/${APP_NAME}/templates/secret.yaml"
echo "   - charts/${APP_NAME}/templates/pvc.yaml"
echo "   - charts/${APP_NAME}/templates/hpa.yaml"
echo "   - charts/${APP_NAME}/templates/servicemonitor.yaml"
echo "   - charts/${APP_NAME}/templates/ingress.yaml"
echo "   - charts/${APP_NAME}/templates/NOTES.txt"
echo "   - charts/${APP_NAME}/templates/_helpers.tpl"
echo ""
echo "🔧 다음 단계:"
echo "1. values.yaml의 secrets 섹션에서 실제 패스워드로 변경"
echo "2. GitHub Actions 워크플로우 생성 스크립트 실행"
echo "3. Helm 차트 검증: helm lint charts/${APP_NAME}"
echo "4. 테스트 배포: helm install --dry-run --debug ${APP_NAME}-test charts/${APP_NAME}"