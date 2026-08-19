{{- define "aegis-ai.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "aegis-ai.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "aegis-ai.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "aegis-ai.labels" -}}
app.kubernetes.io/name: {{ include "aegis-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
