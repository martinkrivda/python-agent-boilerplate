{{- define "python-agent-boilerplate.name" -}}
{{- .Chart.Name }}
{{- end }}

{{- define "python-agent-boilerplate.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "python-agent-boilerplate.labels" -}}
app.kubernetes.io/name: {{ include "python-agent-boilerplate.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
