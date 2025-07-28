{{/*
Expand the name of the chart.
*/}}
{{- define "blacklist.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
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
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: blacklist-microservice
infrastructure: jclee.me
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
Generate basic auth secret data
*/}}
{{- define "blacklist.secretData" -}}
{{- $regtech := printf "%s:%s" (.Values.auth.regtech.username | default "admin") (.Values.auth.regtech.password | default "password") | b64enc }}
{{- $secudium := printf "%s:%s" (.Values.auth.secudium.username | default "admin") (.Values.auth.secudium.password | default "password") | b64enc }}
regtech-username: {{ .Values.auth.regtech.username | default "admin" | b64enc }}
regtech-password: {{ .Values.auth.regtech.password | default "password" | b64enc }}
secudium-username: {{ .Values.auth.secudium.username | default "admin" | b64enc }}
secudium-password: {{ .Values.auth.secudium.password | default "password" | b64enc }}
{{- end }}

{{/*
Generate registry secret for private registry access
*/}}
{{- define "blacklist.registrySecret" -}}
{{- $registry := .Values.image.repository | default "https://registry.jclee.me" }}
{{- $username := .Values.registryAuth.username | default "admin" }}
{{- $password := .Values.registryAuth.password | default "bingogo1" }}
{{- $auth := printf "%s:%s" $username $password | b64enc }}
{{- $dockerConfig := printf `{"auths":{"%s":{"username":"%s","password":"%s","auth":"%s"}}}` $registry $username $password $auth | b64enc }}
.dockerconfigjson: {{ $dockerConfig }}
{{- end }}