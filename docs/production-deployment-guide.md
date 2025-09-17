# S.C.O.U.T. Platform Production Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Application Configuration](#application-configuration)
5. [Docker Deployment](#docker-deployment)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [CI/CD Pipeline Setup](#cicd-pipeline-setup)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Security Configuration](#security-configuration)
10. [Performance Optimization](#performance-optimization)
11. [Backup and Recovery](#backup-and-recovery)
12. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum Production Environment:**
- CPU: 4 cores (8 recommended)
- Memory: 8GB RAM (16GB recommended)
- Storage: 100GB SSD (250GB recommended)
- Network: 1Gbps connection

**Software Requirements:**
- Docker 24.0+
- Kubernetes 1.28+
- PostgreSQL 15+
- Redis 7.0+
- Azure CLI 2.50+

### Cloud Infrastructure

**Azure Resources Required:**
- Azure Kubernetes Service (AKS) cluster
- Azure Database for PostgreSQL Flexible Server
- Azure Cache for Redis
- Azure Container Registry (ACR)
- Azure Key Vault
- Azure OpenAI Service
- Azure Load Balancer
- Azure Application Gateway (optional)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/scout-platform.git
cd scout-platform
```

### 2. Environment Variables

Create production environment file:

```bash
# Copy template
cp .env.example .env.production

# Edit production settings
nano .env.production
```

**Required Environment Variables:**

```env
# Application Settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secure-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database Configuration
DATABASE_URL=postgresql://username:password@your-postgres-server:5432/scout_platform
DATABASE_POOL_SIZE=20
DATABASE_POOL_MAX_OVERFLOW=30
DATABASE_POOL_PRE_PING=true
DATABASE_POOL_RECYCLE=3600

# Redis Configuration
REDIS_URL=rediss://username:password@your-redis-server:6380/0
REDIS_POOL_MAX_CONNECTIONS=50
REDIS_SSL_CERT_REQS=required

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-api-key
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Security Settings
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
PASSWORD_MIN_LENGTH=12
MAX_FAILED_LOGIN_ATTEMPTS=5

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_PER_DAY=10000

# Monitoring
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
LOG_LEVEL=INFO
```

## Database Setup

### 1. Create Azure PostgreSQL Server

```bash
# Create resource group
az group create --name scout-platform-rg --location eastus

# Create PostgreSQL server
az postgres flexible-server create \
  --resource-group scout-platform-rg \
  --name scout-platform-db \
  --location eastus \
  --admin-user dbadmin \
  --admin-password 'YourSecurePassword123!' \
  --sku-name Standard_D2s_v3 \
  --tier GeneralPurpose \
  --storage-size 128 \
  --version 15
```

### 2. Configure Database Security

```bash
# Configure firewall rules
az postgres flexible-server firewall-rule create \
  --resource-group scout-platform-rg \
  --name scout-platform-db \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Enable SSL
az postgres flexible-server parameter set \
  --resource-group scout-platform-rg \
  --server-name scout-platform-db \
  --name require_secure_transport \
  --value on
```

### 3. Initialize Database

```bash
# Connect to database
psql "host=scout-platform-db.postgres.database.azure.com port=5432 dbname=postgres user=dbadmin password=YourSecurePassword123! sslmode=require"

# Create application database
CREATE DATABASE scout_platform;
CREATE USER scout_app WITH ENCRYPTED PASSWORD 'AppSecurePassword123!';
GRANT ALL PRIVILEGES ON DATABASE scout_platform TO scout_app;

# Create extensions
\c scout_platform
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
```

### 4. Run Database Migrations

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run migrations
export DATABASE_URL="postgresql://scout_app:AppSecurePassword123!@scout-platform-db.postgres.database.azure.com:5432/scout_platform"
alembic upgrade head
```

## Application Configuration

### 1. Security Configuration

**Configure Azure Key Vault:**

```bash
# Create Key Vault
az keyvault create \
  --name scout-platform-kv \
  --resource-group scout-platform-rg \
  --location eastus \
  --sku premium

# Store secrets
az keyvault secret set --vault-name scout-platform-kv --name "secret-key" --value "your-super-secure-secret-key"
az keyvault secret set --vault-name scout-platform-kv --name "jwt-secret" --value "your-jwt-secret-key"
az keyvault secret set --vault-name scout-platform-kv --name "database-password" --value "AppSecurePassword123!"
```

### 2. SSL/TLS Configuration

**Generate SSL certificates:**

```bash
# Using Let's Encrypt with cert-manager (recommended)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@yourdomain.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## Docker Deployment

### 1. Build Production Images

```bash
# Build backend image
cd backend
docker build -t scout-platform-backend:latest -f Dockerfile .

# Build frontend image
cd ../frontend
docker build -t scout-platform-frontend:latest .

# Tag images for registry
docker tag scout-platform-backend:latest your-registry.azurecr.io/scout-platform-backend:latest
docker tag scout-platform-frontend:latest your-registry.azurecr.io/scout-platform-frontend:latest
```

### 2. Push to Azure Container Registry

```bash
# Login to ACR
az acr login --name your-registry

# Push images
docker push your-registry.azurecr.io/scout-platform-backend:latest
docker push your-registry.azurecr.io/scout-platform-frontend:latest
```

### 3. Docker Compose Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    image: your-registry.azurecr.io/scout-platform-backend:latest
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    image: your-registry.azurecr.io/scout-platform-frontend:latest
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

## Kubernetes Deployment

### 1. Create AKS Cluster

```bash
# Create AKS cluster
az aks create \
  --resource-group scout-platform-rg \
  --name scout-platform-aks \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-addons monitoring \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 10 \
  --network-plugin azure \
  --network-policy azure

# Get credentials
az aks get-credentials --resource-group scout-platform-rg --name scout-platform-aks
```

### 2. Deploy Application

```bash
# Apply configurations
kubectl apply -f infrastructure/kubernetes/config.yaml
kubectl apply -f infrastructure/kubernetes/backend-deployment.yaml

# Verify deployment
kubectl get pods -n scout-platform
kubectl get services -n scout-platform
```

### 3. Configure Ingress

```bash
# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Apply ingress configuration
kubectl apply -f infrastructure/kubernetes/ingress.yaml
```

## CI/CD Pipeline Setup

### 1. Azure DevOps Setup

1. **Create Azure DevOps Project**
2. **Import repository**
3. **Create service connections**:
   - Azure Resource Manager
   - Azure Container Registry
   - Kubernetes

4. **Configure variable groups**:
   - `Production-Secrets` (linked to Key Vault)
   - `Production-Config`

5. **Create pipeline**:
   ```bash
   # Copy pipeline file
   cp .azure/azure-pipelines.yml azure-pipelines.yml
   
   # Commit and push
   git add azure-pipelines.yml
   git commit -m "Add Azure DevOps pipeline"
   git push origin main
   ```

### 2. GitHub Actions Setup

1. **Add repository secrets**:
   - `AZURE_CREDENTIALS`
   - `ACR_LOGIN_SERVER`
   - `ACR_USERNAME`
   - `ACR_PASSWORD`
   - `KUBE_CONFIG`

2. **Enable GitHub Actions**:
   ```bash
   # Pipeline is already configured in .github/workflows/ci-cd.yml
   # Just ensure secrets are configured in GitHub repository settings
   ```

## Monitoring and Logging

### 1. Setup Prometheus and Grafana

```bash
# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi

# Install Grafana
helm install grafana grafana/grafana \
  --namespace monitoring \
  --set persistence.enabled=true \
  --set persistence.size=10Gi \
  --set adminPassword='SecureGrafanaPassword123!'
```

### 2. Configure Application Metrics

```bash
# Apply ServiceMonitor for application metrics
cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: scout-platform-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: scout-platform-backend
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
EOF
```

### 3. Setup Centralized Logging

```bash
# Install ELK Stack
helm repo add elastic https://helm.elastic.co
helm repo update

# Install Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace \
  --set replicas=3 \
  --set volumeClaimTemplate.resources.requests.storage=30Gi

# Install Kibana
helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=LoadBalancer

# Install Filebeat
helm install filebeat elastic/filebeat \
  --namespace logging
```

## Security Configuration

### 1. Network Security

```bash
# Apply network policies
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: scout-platform-network-policy
  namespace: scout-platform
spec:
  podSelector:
    matchLabels:
      app: scout-platform-backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 5432  # PostgreSQL
    - protocol: TCP
      port: 6379  # Redis
    - protocol: TCP
      port: 443   # HTTPS
EOF
```

### 2. Pod Security Standards

```bash
# Apply pod security policy
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: scout-platform
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
EOF
```

### 3. RBAC Configuration

```bash
# Apply RBAC policies (already included in backend-deployment.yaml)
kubectl apply -f infrastructure/kubernetes/rbac.yaml
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Create performance indexes
CREATE INDEX CONCURRENTLY idx_jobs_company_id ON jobs(company_id);
CREATE INDEX CONCURRENTLY idx_jobs_created_at ON jobs(created_at);
CREATE INDEX CONCURRENTLY idx_candidates_email ON candidates(email);
CREATE INDEX CONCURRENTLY idx_assessments_job_id ON assessments(job_id);
CREATE INDEX CONCURRENTLY idx_assessments_candidate_id ON assessments(candidate_id);

-- Enable query performance insights
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
SELECT pg_reload_conf();
```

### 2. Application Performance

```bash
# Configure resource limits in Kubernetes
kubectl patch deployment scout-platform-backend -n scout-platform -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "backend",
            "resources": {
              "limits": {
                "cpu": "2000m",
                "memory": "4Gi"
              },
              "requests": {
                "cpu": "500m",
                "memory": "1Gi"
              }
            }
          }
        ]
      }
    }
  }
}'
```

### 3. CDN and Caching

```bash
# Configure Azure CDN (using Azure CLI)
az cdn profile create \
  --resource-group scout-platform-rg \
  --name scout-platform-cdn \
  --sku Standard_Microsoft

az cdn endpoint create \
  --resource-group scout-platform-rg \
  --profile-name scout-platform-cdn \
  --name scout-platform-static \
  --origin your-domain.com
```

## Backup and Recovery

### 1. Database Backup

```bash
# Configure automated backups for PostgreSQL
az postgres flexible-server parameter set \
  --resource-group scout-platform-rg \
  --server-name scout-platform-db \
  --name backup_retention_days \
  --value 30

# Manual backup
pg_dump "host=scout-platform-db.postgres.database.azure.com port=5432 dbname=scout_platform user=dbadmin sslmode=require" \
  --format=custom \
  --compress=9 \
  --file="scout_platform_backup_$(date +%Y%m%d_%H%M%S).dump"
```

### 2. Application Backup

```bash
# Backup persistent volumes
kubectl get pv
kubectl apply -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: scout-platform-backup-$(date +%Y%m%d)
  namespace: scout-platform
spec:
  source:
    persistentVolumeClaimName: redis-data
  volumeSnapshotClassName: csi-azuredisk-vsc
EOF
```

### 3. Configuration Backup

```bash
# Backup Kubernetes configurations
kubectl get all -n scout-platform -o yaml > scout-platform-k8s-backup.yaml
kubectl get configmaps -n scout-platform -o yaml >> scout-platform-k8s-backup.yaml
kubectl get secrets -n scout-platform -o yaml >> scout-platform-k8s-backup.yaml
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database connectivity
   kubectl exec -it deployment/scout-platform-backend -n scout-platform -- \
     python -c "import psycopg2; print('Connection successful')"
   
   # Check database logs
   az postgres flexible-server logs list --resource-group scout-platform-rg --name scout-platform-db
   ```

2. **Redis Connection Issues**
   ```bash
   # Test Redis connection
   kubectl exec -it deployment/redis -n scout-platform -- redis-cli ping
   
   # Check Redis logs
   kubectl logs deployment/redis -n scout-platform
   ```

3. **Application Startup Issues**
   ```bash
   # Check application logs
   kubectl logs deployment/scout-platform-backend -n scout-platform --tail=100
   
   # Check pod status
   kubectl describe pod -l app=scout-platform-backend -n scout-platform
   ```

4. **SSL/TLS Issues**
   ```bash
   # Check certificate status
   kubectl get certificates -n scout-platform
   kubectl describe certificate scout-platform-tls -n scout-platform
   
   # Check cert-manager logs
   kubectl logs -n cert-manager deployment/cert-manager
   ```

### Health Checks

```bash
# Application health
curl -f http://your-domain.com/api/v1/health

# Database health
curl -f http://your-domain.com/api/v1/health/db

# Redis health
curl -f http://your-domain.com/api/v1/health/cache

# Detailed system status
curl -f http://your-domain.com/api/v1/health/detailed
```

### Performance Monitoring

```bash
# Monitor resource usage
kubectl top nodes
kubectl top pods -n scout-platform

# Check application metrics
curl http://your-domain.com/metrics

# Database performance
az postgres flexible-server show --resource-group scout-platform-rg --name scout-platform-db
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly Tasks**:
   - Review application logs
   - Check resource utilization
   - Verify backup integrity
   - Update dependencies

2. **Monthly Tasks**:
   - Security patch updates
   - Performance optimization review
   - Capacity planning assessment
   - Documentation updates

3. **Quarterly Tasks**:
   - Security audit
   - Disaster recovery testing
   - Architecture review
   - Cost optimization

### Contact Information

- **Development Team**: dev-team@yourcompany.com
- **DevOps Team**: devops@yourcompany.com
- **Security Team**: security@yourcompany.com
- **On-call Support**: +1-XXX-XXX-XXXX

---

This deployment guide provides comprehensive instructions for deploying the S.C.O.U.T. platform to production. Follow each section carefully and ensure all prerequisites are met before proceeding with the deployment.