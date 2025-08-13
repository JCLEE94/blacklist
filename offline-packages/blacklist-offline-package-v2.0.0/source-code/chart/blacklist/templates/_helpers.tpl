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

{{/*
Create the name of the service account to use
*/}}
{{- define "blacklist.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "blacklist.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Redis connection string
*/}}
{{- define "blacklist.redisUrl" -}}
{{- if .Values.redis.enabled -}}
redis://{{ include "blacklist.fullname" . }}-redis:6379/0
{{- else -}}
memory://localhost
{{- end -}}
{{- end }}

{{/*
Database URL
*/}}
{{- define "blacklist.databaseUrl" -}}
{{- if .Values.persistence.data.enabled -}}
sqlite:////app/instance/blacklist.db
{{- else -}}
sqlite:///:memory:
{{- end -}}
{{- end }}

{{/*
Security context for containers
*/}}
{{- define "blacklist.securityContext" -}}
{{- with .Values.containerSecurityContext }}
{{- toYaml . }}
{{- end }}
{{- end }}

{{/*
Pod security context
*/}}
{{- define "blacklist.podSecurityContext" -}}
{{- with .Values.securityContext }}
{{- toYaml . }}
{{- end }}
{{- end }}

{{/*
Image pull secrets
*/}}
{{- define "blacklist.imagePullSecrets" -}}
{{- if .Values.imagePullSecrets }}
imagePullSecrets:
  {{- range .Values.imagePullSecrets }}
  - name: {{ . | quote }}
  {{- end }}
{{- end }}
{{- end }}