# Quick Deployment Script for S.C.O.U.T. Platform in Azure India
# Subscription: ba2303a2-dc50-41e3-9275-fb26eff7a6bd
# Region: Central India
# Resource Group: scout-platform-rg

# =====================================
# STEP 1: LOGIN AND SETUP (MANDATORY)
# =====================================
az login
az account set --subscription "ba2303a2-dc50-41e3-9275-fb26eff7a6bd"
az group create --name scout-platform-rg --location centralindia

# =====================================
# STEP 2: CONTAINER REGISTRY (MANDATORY)
# =====================================
az acr create --resource-group scout-platform-rg --name scoutplatformacr --sku Basic --admin-enabled true --location centralindia
az acr login --name scoutplatformacr

# =====================================
# STEP 3: DATABASE & CACHE (MANDATORY)
# =====================================
az postgres flexible-server create --resource-group scout-platform-rg --name scout-platform-postgres --location centralindia --admin-user scoutadmin --admin-password "Scout@Platform2024!" --sku-name Standard_B1ms --tier Burstable --storage-size 32 --version 15

az postgres flexible-server db create --resource-group scout-platform-rg --server-name scout-platform-postgres --database-name scout_production

az postgres flexible-server firewall-rule create --resource-group scout-platform-rg --name scout-platform-postgres --rule-name AllowAzure --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0

az redis create --resource-group scout-platform-rg --name scout-platform-redis --location centralindia --sku Basic --vm-size c0

# =====================================
# STEP 4: AI SERVICE (MANDATORY)
# =====================================
az cognitiveservices account create --name scout-platform-openai --resource-group scout-platform-rg --location centralindia --kind OpenAI --sku S0

# =====================================
# STEP 5: SECRETS MANAGEMENT (MANDATORY)
# =====================================
az keyvault create --name scout-platform-kv --resource-group scout-platform-rg --location centralindia

# =====================================
# STEP 6: CHOOSE YOUR DEPLOYMENT METHOD
# =====================================

# OPTION A: KUBERNETES (AKS) - RECOMMENDED FOR PRODUCTION
az aks create --resource-group scout-platform-rg --name scout-platform-aks --location centralindia --node-count 2 --node-vm-size Standard_B2s --enable-addons monitoring --attach-acr scoutplatformacr --generate-ssh-keys
az aks get-credentials --resource-group scout-platform-rg --name scout-platform-aks

# OPTION B: CONTAINER APPS - SERVERLESS (EASIER)
az containerapp env create --name scout-platform-env --resource-group scout-platform-rg --location centralindia

# =====================================
# STEP 7: BUILD AND DEPLOY
# =====================================

# From your local machine (in scout-platform directory):
# cd backend
# az acr build --registry scoutplatformacr --image scout-backend:latest .
# cd ../frontend  
# az acr build --registry scoutplatformacr --image scout-frontend:latest .

# =====================================
# GET CONNECTION DETAILS
# =====================================
echo "=== COPY THESE CONNECTION STRINGS ==="
echo "PostgreSQL Connection:"
echo "postgresql://scoutadmin:Scout@Platform2024!@scout-platform-postgres.postgres.database.azure.com:5432/scout_production?sslmode=require"

echo "Redis Connection (get from command below):"
az redis list-keys --resource-group scout-platform-rg --name scout-platform-redis --query "primaryKey" -o tsv

echo "OpenAI API Key (get from command below):"
az cognitiveservices account keys list --name scout-platform-openai --resource-group scout-platform-rg --query "key1" -o tsv

echo "ACR Login Server:"
az acr show --name scoutplatformacr --query "loginServer" -o tsv

echo "=== NEXT STEPS ==="
echo "1. Build and push your Docker images to ACR"
echo "2. Deploy using Kubernetes manifests or Container Apps"
echo "3. Configure your custom domain DNS"
echo "4. Set up SSL certificates"
echo "5. Configure monitoring and alerts"