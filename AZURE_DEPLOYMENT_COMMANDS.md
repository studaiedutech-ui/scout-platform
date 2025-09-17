# S.C.O.U.T. Platform - Complete Azure Deployment Commands
# Copy and paste these commands in order to deploy to Azure

# =====================================
# 1. INITIAL AZURE SETUP
# =====================================

# Login to Azure
az login

# Set your subscription
az account set --subscription "ba2303a2-dc50-41e3-9275-fb26eff7a6bd"

# Create resource group
az group create --name scout-platform-rg --location centralindia

# =====================================
# 2. AZURE CONTAINER REGISTRY (ACR)
# =====================================

# Create Azure Container Registry
az acr create --resource-group scout-platform-rg --name scoutplatformacr --sku Basic --admin-enabled true --location centralindia

# Get ACR login credentials
az acr credential show --name scoutplatformacr

# Login to ACR
az acr login --name scoutplatformacr

# =====================================
# 3. BUILD AND PUSH DOCKER IMAGES
# =====================================

# Build and push backend image
cd backend
az acr build --registry scoutplatformacr --image scout-backend:latest .

# Build and push frontend image
cd ../frontend
az acr build --registry scoutplatformacr --image scout-frontend:latest .

# =====================================
# 4. AZURE KUBERNETES SERVICE (AKS)
# =====================================

# Create AKS cluster
az aks create \
  --resource-group scout-platform-rg \
  --name scout-platform-aks \
  --location centralindia \
  --node-count 2 \
  --node-vm-size Standard_B2s \
  --enable-addons monitoring \
  --attach-acr scoutplatformacr \
  --generate-ssh-keys

# Get AKS credentials
az aks get-credentials --resource-group scout-platform-rg --name scout-platform-aks

# =====================================
# 5. AZURE DATABASE FOR POSTGRESQL
# =====================================

# Create PostgreSQL Flexible Server
az postgres flexible-server create \
  --resource-group scout-platform-rg \
  --name scout-platform-postgres \
  --location centralindia \
  --admin-user scoutadmin \
  --admin-password "Scout@Platform2024!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 15

# Create database
az postgres flexible-server db create \
  --resource-group scout-platform-rg \
  --server-name scout-platform-postgres \
  --database-name scout_production

# Configure firewall to allow AKS
az postgres flexible-server firewall-rule create \
  --resource-group scout-platform-rg \
  --name scout-platform-postgres \
  --rule-name AllowAKS \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 255.255.255.255

# =====================================
# 6. AZURE CACHE FOR REDIS
# =====================================

# Create Redis Cache
az redis create \
  --resource-group scout-platform-rg \
  --name scout-platform-redis \
  --location centralindia \
  --sku Basic \
  --vm-size c0

# Get Redis connection string
az redis list-keys --resource-group scout-platform-rg --name scout-platform-redis

# =====================================
# 7. AZURE OPENAI SERVICE
# =====================================

# Create Cognitive Services account for OpenAI
az cognitiveservices account create \
  --name scout-platform-openai \
  --resource-group scout-platform-rg \
  --location centralindia \
  --kind OpenAI \
  --sku S0

# Get OpenAI keys
az cognitiveservices account keys list \
  --name scout-platform-openai \
  --resource-group scout-platform-rg

# Deploy GPT-4 model
az cognitiveservices account deployment create \
  --name scout-platform-openai \
  --resource-group scout-platform-rg \
  --deployment-name gpt-4 \
  --model-name gpt-4 \
  --model-version "0613" \
  --model-format OpenAI \
  --scale-settings-scale-type "Standard"

# =====================================
# 8. AZURE KEY VAULT (FOR SECRETS)
# =====================================

# Create Key Vault
az keyvault create \
  --name scout-platform-kv \
  --resource-group scout-platform-rg \
  --location centralindia

# Add secrets to Key Vault
az keyvault secret set --vault-name scout-platform-kv --name "database-url" --value "postgresql://scoutadmin:Scout@Platform2024!@scout-platform-postgres.postgres.database.azure.com:5432/scout_production?sslmode=require"

az keyvault secret set --vault-name scout-platform-kv --name "redis-url" --value "REDIS_CONNECTION_STRING_FROM_STEP_6"

az keyvault secret set --vault-name scout-platform-kv --name "openai-api-key" --value "OPENAI_KEY_FROM_STEP_7"

az keyvault secret set --vault-name scout-platform-kv --name "jwt-secret" --value "your-super-secure-jwt-secret-key-here"

# =====================================
# 9. AZURE STORAGE ACCOUNT (FOR FILES)
# =====================================

# Create Storage Account
az storage account create \
  --name scoutplatformstorage \
  --resource-group scout-platform-rg \
  --location centralindia \
  --sku Standard_LRS

# Create blob container
az storage container create \
  --name uploads \
  --account-name scoutplatformstorage \
  --public-access off

# Get storage account key
az storage account keys list \
  --resource-group scout-platform-rg \
  --account-name scoutplatformstorage

# =====================================
# 10. APPLICATION INSIGHTS (MONITORING)
# =====================================

# Create Application Insights
az monitor app-insights component create \
  --app scout-platform-insights \
  --location centralindia \
  --resource-group scout-platform-rg

# Get instrumentation key
az monitor app-insights component show \
  --app scout-platform-insights \
  --resource-group scout-platform-rg

# =====================================
# 11. DEPLOY TO KUBERNETES
# =====================================

# Create namespace
kubectl create namespace scout-platform

# Create secrets in Kubernetes
kubectl create secret generic scout-secrets \
  --from-literal=database-url="postgresql://scoutadmin:Scout@Platform2024!@scout-platform-postgres.postgres.database.azure.com:5432/scout_production?sslmode=require" \
  --from-literal=redis-url="REDIS_CONNECTION_STRING" \
  --from-literal=openai-api-key="YOUR_OPENAI_API_KEY" \
  --from-literal=jwt-secret="your-super-secure-jwt-secret-key" \
  --namespace scout-platform

# Apply Kubernetes manifests
kubectl apply -f infrastructure/kubernetes/ --namespace scout-platform

# =====================================
# 12. CONFIGURE INGRESS (OPTIONAL)
# =====================================

# Install NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Get external IP
kubectl get service ingress-nginx-controller --namespace ingress-nginx

# =====================================
# 13. AZURE CONTAINER APPS (ALTERNATIVE)
# =====================================

# Create Container Apps Environment
az containerapp env create \
  --name scout-platform-env \
  --resource-group scout-platform-rg \
  --location centralindia

# Deploy backend container app
az containerapp create \
  --name scout-backend \
  --resource-group scout-platform-rg \
  --environment scout-platform-env \
  --image scoutplatformacr.azurecr.io/scout-backend:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 10

# Deploy frontend container app
az containerapp create \
  --name scout-frontend \
  --resource-group scout-platform-rg \
  --environment scout-platform-env \
  --image scoutplatformacr.azurecr.io/scout-frontend:latest \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 5

# =====================================
# 14. AZURE STATIC WEB APPS (FRONTEND ONLY)
# =====================================

# Create Static Web App
az staticwebapp create \
  --name scout-platform-frontend \
  --resource-group scout-platform-rg \
  --source https://github.com/studaiedutech-ui/scout-platform \
  --branch main \
  --app-location "/frontend" \
  --api-location "/backend" \
  --output-location "/frontend/build"

# =====================================
# 15. VERIFY DEPLOYMENT
# =====================================

# Check AKS deployment status
kubectl get pods --namespace scout-platform
kubectl get services --namespace scout-platform
kubectl get ingress --namespace scout-platform

# Check Container Apps
az containerapp list --resource-group scout-platform-rg --output table

# =====================================
# 16. CLEANUP (IF NEEDED)
# =====================================

# Delete everything (use with caution!)
# az group delete --name scout-platform-rg --yes --no-wait

# =====================================
# IMPORTANT NOTES:
# =====================================
# 1. Using subscription: ba2303a2-dc50-41e3-9275-fb26eff7a6bd
# 2. Deployed in Central India region for optimal performance
# 3. Resource group: scout-platform-rg
# 4. Custom domain suggestions: scout-platform.com or scoutplatform.in
# 5. Replace connection strings and API keys with actual values from previous steps
# 6. Update firewall rules based on your security requirements
# 7. Consider using Azure Key Vault CSI driver for better secret management
# 8. Set up Azure Monitor alerts for production monitoring
# 9. Configure backup strategies for databases and storage
# 10. For custom domain, you'll need to configure DNS and SSL certificates

# =====================================
# DOMAIN CONFIGURATION (OPTIONAL)
# =====================================

# If you have a custom domain (e.g., scout-platform.com), configure DNS:
# 1. Create Azure DNS Zone (if using Azure DNS)
az network dns zone create \
  --resource-group scout-platform-rg \
  --name scout-platform.com

# 2. Get name servers
az network dns zone show \
  --resource-group scout-platform-rg \
  --name scout-platform.com \
  --query "nameServers"

# 3. Create SSL certificate (use Azure Key Vault)
az keyvault certificate create \
  --vault-name scout-platform-kv \
  --name scout-platform-ssl \
  --policy "$(az keyvault certificate get-default-policy)"

# =====================================
# INDIA-SPECIFIC OPTIMIZATIONS
# =====================================

# Enable Azure Front Door for better performance across India
az network front-door create \
  --resource-group scout-platform-rg \
  --name scout-platform-fd \
  --accepted-protocols Http Https \
  --backend-host-header scout-platform.com \
  --forwarding-protocol HttpsOnly

# Configure CDN for static assets (optimized for India)
az cdn profile create \
  --resource-group scout-platform-rg \
  --name scout-platform-cdn \
  --sku Standard_Microsoft

# =====================================
# MONITORING & ALERTS FOR INDIA TIMEZONE
# =====================================

# Set up alerts for IST timezone
az monitor action-group create \
  --resource-group scout-platform-rg \
  --name scout-platform-alerts \
  --short-name scout-alerts

# Create availability test for monitoring
az monitor app-insights web-test create \
  --resource-group scout-platform-rg \
  --app-insights scout-platform-insights \
  --name scout-platform-availability \
  --location centralindia \
  --test-locations "Central India" "South India" \
  --web-test-kind ping \
  --web-test-properties url="https://scout-platform.com"