# Quick Deployment Script for S.C.O.U.T. Platform in Azure India (PowerShell)
# Subscription: ba2303a2-dc50-41e3-9275-fb26eff7a6bd
# Region: Central India
# Resource Group: scout-platform-rg

# IMPORTANT: Set database password before running:
# $env:DB_ADMIN_PASSWORD = "YourSecurePassword123!"

# =====================================
# STEP 1: LOGIN AND SETUP (MANDATORY)
# =====================================
Write-Host "Step 1: Setting up Azure subscription and resource group..." -ForegroundColor Green
az login
az account set --subscription "ba2303a2-dc50-41e3-9275-fb26eff7a6bd"
az group create --name scout-platform-rg --location centralindia

# =====================================
# STEP 2: CONTAINER REGISTRY (MANDATORY)
# =====================================
Write-Host "Step 2: Creating Azure Container Registry..." -ForegroundColor Green
az acr create --resource-group scout-platform-rg --name scoutplatformacr --sku Basic --admin-enabled true --location centralindia
az acr login --name scoutplatformacr

# =====================================
# STEP 3: DATABASE & CACHE (MANDATORY)
# =====================================
Write-Host "Step 3: Creating PostgreSQL database and Redis cache..." -ForegroundColor Green
az postgres flexible-server create --resource-group scout-platform-rg --name scout-platform-postgres --location centralindia --admin-user scoutadmin --admin-password "$env:DB_ADMIN_PASSWORD" --sku-name Standard_B1ms --tier Burstable --storage-size 32 --version 15

az postgres flexible-server db create --resource-group scout-platform-rg --server-name scout-platform-postgres --database-name scout_production

az postgres flexible-server firewall-rule create --resource-group scout-platform-rg --name scout-platform-postgres --rule-name AllowAzure --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0

az redis create --resource-group scout-platform-rg --name scout-platform-redis --location centralindia --sku Basic --vm-size c0

# =====================================
# STEP 4: AI SERVICE (MANDATORY)
# =====================================
Write-Host "Step 4: Creating Azure OpenAI service..." -ForegroundColor Green
az cognitiveservices account create --name scout-platform-openai --resource-group scout-platform-rg --location centralindia --kind OpenAI --sku S0

# =====================================
# STEP 5: SECRETS MANAGEMENT (MANDATORY)
# =====================================
Write-Host "Step 5: Creating Key Vault for secrets..." -ForegroundColor Green
az keyvault create --name scout-platform-kv --resource-group scout-platform-rg --location centralindia

# =====================================
# STEP 6: CHOOSE YOUR DEPLOYMENT METHOD
# =====================================
Write-Host "Step 6: Choose your deployment method..." -ForegroundColor Yellow
Write-Host "Option A: Kubernetes (AKS) - Recommended for production"
Write-Host "Option B: Container Apps - Serverless (easier)"

$deploymentChoice = Read-Host "Enter 'A' for AKS or 'B' for Container Apps"

if ($deploymentChoice -eq "A" -or $deploymentChoice -eq "a") {
    Write-Host "Creating AKS cluster..." -ForegroundColor Green
    az aks create --resource-group scout-platform-rg --name scout-platform-aks --location centralindia --node-count 2 --node-vm-size Standard_B2s --enable-addons monitoring --attach-acr scoutplatformacr --generate-ssh-keys
    az aks get-credentials --resource-group scout-platform-rg --name scout-platform-aks
    Write-Host "AKS cluster created successfully!" -ForegroundColor Green
} elseif ($deploymentChoice -eq "B" -or $deploymentChoice -eq "b") {
    Write-Host "Creating Container Apps environment..." -ForegroundColor Green
    az containerapp env create --name scout-platform-env --resource-group scout-platform-rg --location centralindia
    Write-Host "Container Apps environment created successfully!" -ForegroundColor Green
}

# =====================================
# STEP 7: BUILD AND DEPLOY IMAGES
# =====================================
Write-Host "Step 7: Building and pushing Docker images..." -ForegroundColor Green
Write-Host "Building backend image..."
Set-Location -Path "backend"
az acr build --registry scoutplatformacr --image scout-backend:latest .

Write-Host "Building frontend image..."
Set-Location -Path "..\frontend"
az acr build --registry scoutplatformacr --image scout-frontend:latest .

Set-Location -Path ".."

# =====================================
# GET CONNECTION DETAILS
# =====================================
Write-Host "=== DEPLOYMENT COMPLETED! ===" -ForegroundColor Green
Write-Host "=== COPY THESE CONNECTION STRINGS ===" -ForegroundColor Yellow

Write-Host "PostgreSQL Connection String:" -ForegroundColor Cyan
Write-Host "postgresql://scoutadmin:Scout@Platform2024!@scout-platform-postgres.postgres.database.azure.com:5432/scout_production?sslmode=require"

Write-Host "`nRedis Connection String:" -ForegroundColor Cyan
$redisKey = az redis list-keys --resource-group scout-platform-rg --name scout-platform-redis --query "primaryKey" -o tsv
Write-Host "scout-platform-redis.redis.cache.windows.net:6380,password=$redisKey,ssl=True,abortConnect=False"

Write-Host "`nOpenAI API Key:" -ForegroundColor Cyan
$openaiKey = az cognitiveservices account keys list --name scout-platform-openai --resource-group scout-platform-rg --query "key1" -o tsv
Write-Host $openaiKey

Write-Host "`nOpenAI Endpoint:" -ForegroundColor Cyan
$openaiEndpoint = az cognitiveservices account show --name scout-platform-openai --resource-group scout-platform-rg --query "properties.endpoint" -o tsv
Write-Host $openaiEndpoint

Write-Host "`nACR Login Server:" -ForegroundColor Cyan
$acrServer = az acr show --name scoutplatformacr --query "loginServer" -o tsv
Write-Host $acrServer

Write-Host "`n=== NEXT STEPS ===" -ForegroundColor Green
Write-Host "1. Images have been built and pushed to ACR ✅"
Write-Host "2. Update your environment variables with the connection strings above"
Write-Host "3. Deploy using Kubernetes manifests (if AKS) or create Container Apps (if Container Apps)"
Write-Host "4. Configure your custom domain DNS"
Write-Host "5. Set up SSL certificates"
Write-Host "6. Configure monitoring and alerts"

Write-Host "`nDeployment Summary:" -ForegroundColor Magenta
Write-Host "- Subscription: ba2303a2-dc50-41e3-9275-fb26eff7a6bd"
Write-Host "- Region: Central India"
Write-Host "- Resource Group: scout-platform-rg"
Write-Host "- Status: Ready for production deployment 🚀"