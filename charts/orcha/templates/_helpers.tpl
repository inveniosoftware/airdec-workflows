{{/*
Expand the name of the chart.
*/}}
{{- define "orcha.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "orcha.fullname" -}}
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
{{- define "orcha.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "orcha.labels" -}}
helm.sh/chart: {{ include "orcha.chart" . }}
{{ include "orcha.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "orcha.selectorLabels" -}}
app.kubernetes.io/name: {{ include "orcha.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Database Host
*/}}
{{- define "orcha.databaseHost" -}}
{{- if .Values.externalDatabase.enabled }}
{{- .Values.externalDatabase.host }}
{{- else }}
{{- .Values.postgresql.fullnameOverride | default "orcha-db" }}
{{- end }}
{{- end }}

{{/*
Database Port
*/}}
{{- define "orcha.databasePort" -}}
{{- if .Values.externalDatabase.enabled }}
{{- .Values.externalDatabase.port }}
{{- else }}
{{- "5432" }}
{{- end }}
{{- end }}

{{/*
Database User
*/}}
{{- define "orcha.databaseUser" -}}
{{- if .Values.externalDatabase.enabled }}
{{- .Values.externalDatabase.user }}
{{- else }}
{{- .Values.postgresql.auth.username }}
{{- end }}
{{- end }}

{{/*
Database Name
*/}}
{{- define "orcha.databaseName" -}}
{{- if .Values.externalDatabase.enabled }}
{{- .Values.externalDatabase.database }}
{{- else }}
{{- .Values.postgresql.auth.database }}
{{- end }}
{{- end }}

{{/*
Database Secret Name
*/}}
{{- define "orcha.dbSecretName" -}}
{{- if .Values.secrets.db.existingSecret }}
{{- .Values.secrets.db.existingSecret }}
{{- else }}
{{- "db-secrets" }}
{{- end }}
{{- end }}

{{/*
LLM Secret Name
*/}}
{{- define "orcha.llmSecretName" -}}
{{- if .Values.secrets.llm.existingSecret }}
{{- .Values.secrets.llm.existingSecret }}
{{- else }}
{{- "llm-secrets" }}
{{- end }}
{{- end }}

{{/*
Temporal Hostname
*/}}
{{- define "orcha.temporalHost" -}}
{{- printf "%s-temporal-frontend:7233" .Release.Name }}
{{- end }}

{{/*
Temporal Fullname
*/}}
{{- define "orcha.temporalFullname" -}}
{{- if .Values.temporal.fullnameOverride }}
{{- .Values.temporal.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default "temporal" .Values.temporal.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Temporal Web Service Name
*/}}
{{- define "orcha.temporalWebServiceName" -}}
{{- if .Values.route.temporalWeb.serviceName }}
{{- .Values.route.temporalWeb.serviceName }}
{{- else }}
{{- printf "%s-web" (include "orcha.temporalFullname" .) }}
{{- end }}
{{- end }}
