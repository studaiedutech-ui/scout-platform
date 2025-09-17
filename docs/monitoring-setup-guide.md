# S.C.O.U.T. Platform Monitoring Setup Guide

## Table of Contents

1. [Monitoring Overview](#monitoring-overview)
2. [Prometheus Setup](#prometheus-setup)
3. [Grafana Configuration](#grafana-configuration)
4. [Alert Manager](#alert-manager)
5. [Application Metrics](#application-metrics)
6. [Infrastructure Monitoring](#infrastructure-monitoring)
7. [Log Management](#log-management)
8. [Health Checks](#health-checks)
9. [Performance Monitoring](#performance-monitoring)
10. [Incident Response](#incident-response)

## Monitoring Overview

The S.C.O.U.T. platform implements comprehensive monitoring across all infrastructure and application layers to ensure optimal performance, reliability, and early issue detection.

### Monitoring Stack

- **Metrics Collection**: Prometheus
- **Visualization**: Grafana
- **Alerting**: AlertManager + PagerDuty
- **Log Management**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **APM**: Azure Application Insights
- **Infrastructure**: Azure Monitor + Prometheus Node Exporter

### Key Monitoring Principles

1. **Proactive Monitoring**: Detect issues before they impact users
2. **Full Stack Coverage**: Monitor from infrastructure to application
3. **Meaningful Alerts**: Focus on actionable alerts, reduce noise
4. **Performance Insights**: Track user experience and system performance
5. **Security Monitoring**: Detect and respond to security threats

## Prometheus Setup

### Installation

```bash
# Create monitoring namespace
kubectl create namespace monitoring

# Add Prometheus Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus Operator
helm install prometheus-operator prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
  --set grafana.adminPassword='SecureGrafanaPassword123!' \
  --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.resources.requests.storage=10Gi
```

### Prometheus Configuration

Create `prometheus-config.yaml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  # Kubernetes API Server
  - job_name: 'kubernetes-apiservers'
    kubernetes_sd_configs:
    - role: endpoints
    scheme: https
    tls_config:
      ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabel_configs:
    - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
      action: keep
      regex: default;kubernetes;https

  # Scout Platform Application
  - job_name: 'scout-platform-backend'
    kubernetes_sd_configs:
    - role: endpoints
      namespaces:
        names:
        - scout-platform
    relabel_configs:
    - source_labels: [__meta_kubernetes_service_name]
      action: keep
      regex: scout-platform-backend
    - source_labels: [__meta_kubernetes_endpoint_port_name]
      action: keep
      regex: metrics

  # Node Exporter
  - job_name: 'node-exporter'
    kubernetes_sd_configs:
    - role: endpoints
    relabel_configs:
    - source_labels: [__meta_kubernetes_service_name]
      action: keep
      regex: node-exporter

  # PostgreSQL Exporter
  - job_name: 'postgres-exporter'
    static_configs:
    - targets: ['postgres-exporter:9187']

  # Redis Exporter
  - job_name: 'redis-exporter'
    static_configs:
    - targets: ['redis-exporter:9121']

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alertmanager:9093
```

### Application Metrics Configuration

Add to your FastAPI application (`app/core/metrics.py`):

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI
from fastapi.responses import Response
import time
import psutil

# Metrics definitions
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'active_database_connections',
    'Number of active database connections'
)

MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

CPU_USAGE = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

AUTHENTICATION_ATTEMPTS = Counter(
    'authentication_attempts_total',
    'Total authentication attempts',
    ['status']
)

JOB_APPLICATIONS = Counter(
    'job_applications_total',
    'Total job applications',
    ['job_id']
)

AI_ASSESSMENTS = Counter(
    'ai_assessments_total',
    'Total AI assessments',
    ['status']
)

AI_ASSESSMENT_DURATION = Histogram(
    'ai_assessment_duration_seconds',
    'AI assessment duration in seconds'
)

def setup_metrics(app: FastAPI):
    """Setup metrics collection for the application"""
    
    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
    
    @app.get("/metrics")
    async def metrics():
        """Expose metrics for Prometheus scraping"""
        
        # Update system metrics
        MEMORY_USAGE.set(psutil.virtual_memory().used)
        CPU_USAGE.set(psutil.cpu_percent())
        
        return Response(
            generate_latest(),
            media_type="text/plain"
        )

# Helper functions for custom metrics
def record_authentication_attempt(status: str):
    """Record authentication attempt"""
    AUTHENTICATION_ATTEMPTS.labels(status=status).inc()

def record_job_application(job_id: int):
    """Record job application"""
    JOB_APPLICATIONS.labels(job_id=str(job_id)).inc()

def record_ai_assessment(status: str, duration: float):
    """Record AI assessment"""
    AI_ASSESSMENTS.labels(status=status).inc()
    if status == "completed":
        AI_ASSESSMENT_DURATION.observe(duration)

def update_active_connections(count: int):
    """Update active database connections"""
    ACTIVE_CONNECTIONS.set(count)
```

## Grafana Configuration

### Dashboard Creation

Create `grafana-dashboard.json`:

```json
{
  "dashboard": {
    "id": null,
    "title": "S.C.O.U.T. Platform Dashboard",
    "tags": ["scout-platform"],
    "timezone": "UTC",
    "panels": [
      {
        "id": 1,
        "title": "HTTP Requests per Second",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "yAxes": [
          {
            "label": "Requests/sec"
          }
        ]
      },
      {
        "id": 2,
        "title": "Response Time Percentiles",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "99th percentile"
          }
        ]
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100",
            "legendFormat": "Error Rate %"
          }
        ],
        "thresholds": "5,10"
      },
      {
        "id": 4,
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "active_database_connections",
            "legendFormat": "Active Connections"
          }
        ]
      },
      {
        "id": 5,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "memory_usage_bytes / 1024 / 1024 / 1024",
            "legendFormat": "Memory Usage (GB)"
          }
        ]
      },
      {
        "id": 6,
        "title": "Authentication Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(authentication_attempts_total{status=\"success\"}[5m]) / rate(authentication_attempts_total[5m]) * 100",
            "legendFormat": "Success Rate %"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

### Import Dashboard

```bash
# Apply dashboard using ConfigMap
kubectl create configmap grafana-dashboard-scout \
  --from-file=grafana-dashboard.json \
  -n monitoring

# Label for automatic discovery
kubectl label configmap grafana-dashboard-scout \
  grafana_dashboard=1 \
  -n monitoring
```

## Alert Manager

### AlertManager Configuration

Create `alertmanager-config.yaml`:

```yaml
global:
  smtp_smarthost: 'smtp.company.com:587'
  smtp_from: 'alerts@company.com'
  smtp_auth_username: 'alerts@company.com'
  smtp_auth_password: 'smtp_password'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      severity: warning
    receiver: 'warning-alerts'

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://webhook.company.com'

- name: 'critical-alerts'
  email_configs:
  - to: 'oncall@company.com'
    subject: 'CRITICAL: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
  pagerduty_configs:
  - service_key: 'your-pagerduty-service-key'
    description: '{{ .GroupLabels.alertname }}'

- name: 'warning-alerts'
  email_configs:
  - to: 'devops@company.com'
    subject: 'WARNING: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
    channel: '#alerts'
    title: 'WARNING: {{ .GroupLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### Alert Rules

Create `alert-rules.yaml`:

```yaml
groups:
- name: scout-platform.rules
  rules:
  
  # High Error Rate
  - alert: HighErrorRate
    expr: rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }} for the last 5 minutes"

  # High Response Time
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value }}s"

  # Database Connection Issues
  - alert: DatabaseConnectionHigh
    expr: active_database_connections > 80
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High database connection count"
      description: "Database connections: {{ $value }}"

  - alert: DatabaseConnectionCritical
    expr: active_database_connections > 95
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Critical database connection count"
      description: "Database connections: {{ $value }}"

  # Memory Usage
  - alert: HighMemoryUsage
    expr: (memory_usage_bytes / 1024 / 1024 / 1024) > 3.5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value }}GB"

  - alert: CriticalMemoryUsage
    expr: (memory_usage_bytes / 1024 / 1024 / 1024) > 7
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Critical memory usage"
      description: "Memory usage is {{ $value }}GB"

  # CPU Usage
  - alert: HighCPUUsage
    expr: cpu_usage_percent > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage"
      description: "CPU usage is {{ $value }}%"

  # Authentication Failures
  - alert: HighAuthenticationFailures
    expr: rate(authentication_attempts_total{status="failed"}[5m]) > 10
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High authentication failure rate"
      description: "Authentication failures: {{ $value }} per second"

  # Service Down
  - alert: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service is down"
      description: "{{ $labels.instance }} of job {{ $labels.job }} has been down for more than 1 minute"

  # Disk Space
  - alert: DiskSpaceLow
    expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 20
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Low disk space"
      description: "Disk space is {{ $value }}% on {{ $labels.instance }}"

  - alert: DiskSpaceCritical
    expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 10
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Critical disk space"
      description: "Disk space is {{ $value }}% on {{ $labels.instance }}"
```

Apply the rules:

```bash
kubectl create configmap alert-rules \
  --from-file=alert-rules.yaml \
  -n monitoring

kubectl label configmap alert-rules \
  prometheus=kube-prometheus \
  role=alert-rules \
  -n monitoring
```

## Application Metrics

### Custom Metrics Implementation

Update your FastAPI endpoints to include metrics:

```python
# app/api/endpoints/auth.py
from app.core.metrics import record_authentication_attempt

@router.post("/login")
async def login(request: LoginRequest):
    try:
        # Authentication logic
        user = await authenticate_user(request.email, request.password)
        
        if user:
            record_authentication_attempt("success")
            return {"access_token": token, "user": user}
        else:
            record_authentication_attempt("failed")
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        record_authentication_attempt("error")
        raise

# app/api/endpoints/jobs.py
from app.core.metrics import record_job_application

@router.post("/{job_id}/apply")
async def apply_to_job(job_id: int, application: ApplicationRequest):
    try:
        # Application logic
        result = await create_application(job_id, application)
        record_job_application(job_id)
        return result
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

# app/api/endpoints/assessments.py
from app.core.metrics import record_ai_assessment
import time

@router.post("/")
async def create_assessment(assessment_request: AssessmentRequest):
    start_time = time.time()
    
    try:
        # AI assessment logic
        result = await run_ai_assessment(assessment_request)
        
        duration = time.time() - start_time
        record_ai_assessment("completed", duration)
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        record_ai_assessment("failed", duration)
        raise
```

### Database Metrics

Create database metrics collector (`app/core/db_metrics.py`):

```python
import asyncio
from sqlalchemy import text
from app.core.database import get_database
from app.core.metrics import update_active_connections

async def collect_database_metrics():
    """Collect database performance metrics"""
    
    while True:
        try:
            async with get_database() as db:
                # Active connections
                result = await db.execute(text("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """))
                active_connections = result.scalar()
                update_active_connections(active_connections)
                
                # Other database metrics can be added here
                
        except Exception as e:
            logger.error(f"Database metrics collection error: {e}")
        
        await asyncio.sleep(30)  # Collect every 30 seconds

# Start metrics collection on application startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(collect_database_metrics())
```

## Infrastructure Monitoring

### Node Exporter Setup

```yaml
# node-exporter-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostPID: true
      hostIPC: true
      hostNetwork: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:latest
        ports:
        - containerPort: 9100
        resources:
          requests:
            memory: 30Mi
            cpu: 100m
          limits:
            memory: 50Mi
            cpu: 200m
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /rootfs
          readOnly: true
        args:
        - '--path.procfs=/host/proc'
        - '--path.sysfs=/host/sys'
        - '--collector.filesystem.ignored-mount-points'
        - '^/(sys|proc|dev|host|etc|rootfs/var/lib/docker/containers|rootfs/var/lib/docker/overlay2|rootfs/run/docker/netns|rootfs/var/lib/docker/aufs)($$|/)'
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
      tolerations:
      - operator: Exists
        effect: NoSchedule
```

### PostgreSQL Exporter

```yaml
# postgres-exporter-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-exporter
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres-exporter
  template:
    metadata:
      labels:
        app: postgres-exporter
    spec:
      containers:
      - name: postgres-exporter
        image: prometheuscommunity/postgres-exporter:latest
        ports:
        - containerPort: 9187
        env:
        - name: DATA_SOURCE_NAME
          valueFrom:
            secretKeyRef:
              name: postgres-exporter-secret
              key: data-source-name
        resources:
          requests:
            memory: 64Mi
            cpu: 100m
          limits:
            memory: 128Mi
            cpu: 200m
---
apiVersion: v1
kind: Secret
metadata:
  name: postgres-exporter-secret
  namespace: monitoring
type: Opaque
stringData:
  data-source-name: "postgresql://monitoring_user:password@postgres-host:5432/scout_platform?sslmode=require"
```

## Log Management

### ELK Stack Setup

```bash
# Add Elastic Helm repository
helm repo add elastic https://helm.elastic.co
helm repo update

# Install Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace \
  --set replicas=3 \
  --set volumeClaimTemplate.resources.requests.storage=30Gi \
  --set esConfig."elasticsearch\.yml" |
    cluster.name: "scout-platform-logs"
    network.host: "0.0.0.0"
    xpack.security.enabled: true

# Install Kibana
helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=LoadBalancer \
  --set elasticsearchHosts="http://elasticsearch-master:9200"

# Install Filebeat
helm install filebeat elastic/filebeat \
  --namespace logging \
  --set filebeatConfig."filebeat\.yml" |
    filebeat.inputs:
    - type: container
      paths:
        - /var/log/containers/*.log
      processors:
        - add_kubernetes_metadata:
            host: ${NODE_NAME}
            matchers:
            - logs_path:
                logs_path: "/var/log/containers/"
    output.elasticsearch:
      hosts: ["elasticsearch-master:9200"]
```

### Application Logging Configuration

Update logging configuration (`app/core/logging.py`):

```python
import logging
import json
from pythonjsonlogger import jsonlogger
from datetime import datetime

# Custom JSON formatter
class CustomJSONFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJSONFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add application info
        log_record['application'] = 'scout-platform'
        log_record['environment'] = os.getenv('ENVIRONMENT', 'development')
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'company_id'):
            log_record['company_id'] = record.company_id

def setup_logging():
    """Setup application logging"""
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create handler
    handler = logging.StreamHandler()
    
    # Create formatter
    formatter = CustomJSONFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Security event logging
def log_security_event(event_type: str, details: dict, user_id: str = None):
    """Log security events for monitoring"""
    
    security_logger = logging.getLogger("security")
    
    log_data = {
        "event_type": event_type,
        "details": details,
        "timestamp": datetime.utcnow().isoformat(),
        "severity": "warning" if event_type in ["failed_login", "rate_limit"] else "info"
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    security_logger.warning(json.dumps(log_data))
```

## Health Checks

### Application Health Checks

Enhanced health check endpoint (`app/api/endpoints/health.py`):

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_database
from app.services.azure_openai_service import AzureOpenAIService
import redis
import time
import asyncio

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status"""
    
    components = {}
    overall_status = "healthy"
    
    # Database health check
    try:
        start_time = time.time()
        async with get_database() as db:
            await db.execute(text("SELECT 1"))
        db_response_time = (time.time() - start_time) * 1000
        
        components["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time, 2)
        }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "unhealthy"
    
    # Redis health check
    try:
        start_time = time.time()
        redis_client = redis.from_url(os.getenv("REDIS_URL"))
        redis_client.ping()
        redis_response_time = (time.time() - start_time) * 1000
        
        components["redis"] = {
            "status": "healthy",
            "response_time_ms": round(redis_response_time, 2)
        }
    except Exception as e:
        components["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "unhealthy"
    
    # Azure OpenAI health check
    try:
        start_time = time.time()
        ai_service = AzureOpenAIService()
        # Simple health check call
        await ai_service.health_check()
        ai_response_time = (time.time() - start_time) * 1000
        
        components["azure_openai"] = {
            "status": "healthy",
            "response_time_ms": round(ai_response_time, 2)
        }
    except Exception as e:
        components["azure_openai"] = {
            "status": "degraded",
            "error": str(e)
        }
        if overall_status == "healthy":
            overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "version": "1.0.0",
        "components": components
    }

@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    
    # Check critical dependencies
    try:
        async with get_database() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Not ready")

@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    
    # Basic application responsiveness check
    return {"status": "alive"}
```

### Kubernetes Health Check Configuration

Update deployment with health checks:

```yaml
# backend-deployment.yaml (health check section)
livenessProbe:
  httpGet:
    path: /api/v1/health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/v1/health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /api/v1/health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 30
```

## Performance Monitoring

### Application Performance Monitoring (APM)

Configure Azure Application Insights:

```python
# app/core/apm.py
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
import os

def setup_apm(app):
    """Setup Application Performance Monitoring"""
    
    # Azure Application Insights
    instrumentation_key = os.getenv('APPINSIGHTS_INSTRUMENTATION_KEY')
    
    if instrumentation_key:
        # Tracing
        tracer = Tracer(
            exporter=AzureExporter(
                connection_string=f"InstrumentationKey={instrumentation_key}"
            ),
            sampler=ProbabilitySampler(1.0)  # 100% sampling for demo
        )
        
        # Add middleware for automatic request tracing
        middleware = FlaskMiddleware(
            app,
            exporter=AzureExporter(
                connection_string=f"InstrumentationKey={instrumentation_key}"
            ),
            sampler=ProbabilitySampler(1.0)
        )
```

### Custom Performance Metrics

```python
# app/core/performance.py
import time
import asyncio
from functools import wraps
from app.core.metrics import REQUEST_DURATION

def measure_performance(operation_name: str):
    """Decorator to measure operation performance"""
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                REQUEST_DURATION.labels(
                    method="custom",
                    endpoint=operation_name
                ).observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                REQUEST_DURATION.labels(
                    method="custom",
                    endpoint=operation_name
                ).observe(duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Usage example
@measure_performance("ai_assessment")
async def run_ai_assessment(job_id: int, candidate_id: int):
    # AI assessment logic
    pass
```

## Incident Response

### Incident Response Playbooks

Create incident response procedures:

```yaml
# incident-response-playbooks.yaml
playbooks:
  high_error_rate:
    trigger: "HighErrorRate alert"
    steps:
      1: "Check application logs for error patterns"
      2: "Verify database connectivity and performance"
      3: "Check external service status (Azure OpenAI)"
      4: "Review recent deployments"
      5: "Scale application if needed"
      6: "Contact development team if issue persists"
    
  database_connection_issues:
    trigger: "DatabaseConnectionHigh/Critical alert"
    steps:
      1: "Check database server status"
      2: "Review connection pool settings"
      3: "Identify long-running queries"
      4: "Kill problematic connections if necessary"
      5: "Consider scaling database resources"
      6: "Update connection pool configuration"
    
  service_down:
    trigger: "ServiceDown alert"
    steps:
      1: "Check Kubernetes pod status"
      2: "Review pod logs for startup errors"
      3: "Verify resource availability"
      4: "Check health check endpoints"
      5: "Restart pods if necessary"
      6: "Escalate to development team"
```

### Automated Response Scripts

```bash
#!/bin/bash
# scripts/incident-response.sh

case "$1" in
  "high_error_rate")
    echo "Investigating high error rate..."
    kubectl logs deployment/scout-platform-backend -n scout-platform --tail=100
    kubectl top pods -n scout-platform
    ;;
    
  "scale_up")
    echo "Scaling up application..."
    kubectl scale deployment scout-platform-backend --replicas=5 -n scout-platform
    ;;
    
  "restart_pods")
    echo "Restarting application pods..."
    kubectl rollout restart deployment/scout-platform-backend -n scout-platform
    ;;
    
  *)
    echo "Usage: $0 {high_error_rate|scale_up|restart_pods}"
    exit 1
    ;;
esac
```

### Monitoring Dashboard URLs

- **Grafana Dashboard**: https://grafana.scout-platform.com
- **Prometheus**: https://prometheus.scout-platform.com  
- **AlertManager**: https://alertmanager.scout-platform.com
- **Kibana (Logs)**: https://kibana.scout-platform.com

### Contact Information

**Monitoring Team**:
- Primary: monitoring@company.com
- Secondary: +1-XXX-XXX-XXXX
- Escalation: devops-manager@company.com

**24/7 Operations Center**:
- Email: ops@company.com
- Phone: +1-XXX-XXX-XXXX
- Slack: #ops-alerts

---

This monitoring setup guide provides comprehensive monitoring, alerting, and observability for the S.C.O.U.T. platform. Regular review and updates ensure continued effectiveness in detecting and responding to issues.