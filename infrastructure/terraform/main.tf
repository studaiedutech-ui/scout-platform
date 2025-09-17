terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Resource Group
resource "azurerm_resource_group" "scout_platform" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "scout-platform"
  }
}

# Container Registry
resource "azurerm_container_registry" "scout_platform" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.scout_platform.name
  location           = azurerm_resource_group.scout_platform.location
  sku                = "Standard"
  admin_enabled      = true

  tags = {
    Environment = var.environment
    Project     = "scout-platform"
  }
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "scout_platform" {
  name                = var.aks_cluster_name
  location           = azurerm_resource_group.scout_platform.location
  resource_group_name = azurerm_resource_group.scout_platform.name
  dns_prefix         = "${var.aks_cluster_name}-dns"

  default_node_pool {
    name       = "default"
    node_count = var.aks_node_count
    vm_size    = var.aks_vm_size
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    Environment = var.environment
    Project     = "scout-platform"
  }
}

# Static Web App
resource "azurerm_static_site" "scout_platform" {
  name                = var.static_web_app_name
  resource_group_name = azurerm_resource_group.scout_platform.name
  location           = "East US 2"  # Static Web Apps limited regions
  sku_tier           = "Standard"
  sku_size           = "Standard"

  tags = {
    Environment = var.environment
    Project     = "scout-platform"
  }
}

# PostgreSQL Server
resource "azurerm_postgresql_flexible_server" "scout_platform" {
  name                   = var.postgresql_server_name
  resource_group_name    = azurerm_resource_group.scout_platform.name
  location              = azurerm_resource_group.scout_platform.location
  version               = "15"
  administrator_login    = var.postgresql_admin_username
  administrator_password = var.postgresql_admin_password
  storage_mb            = 32768
  sku_name              = "B_Standard_B1ms"

  tags = {
    Environment = var.environment
    Project     = "scout-platform"
  }
}

# PostgreSQL Database
resource "azurerm_postgresql_flexible_server_database" "scout_platform" {
  name      = "scout_db"
  server_id = azurerm_postgresql_flexible_server.scout_platform.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Redis Cache
resource "azurerm_redis_cache" "scout_platform" {
  name                = var.redis_cache_name
  location           = azurerm_resource_group.scout_platform.location
  resource_group_name = azurerm_resource_group.scout_platform.name
  capacity           = 0
  family             = "C"
  sku_name           = "Standard"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  tags = {
    Environment = var.environment
    Project     = "scout-platform"
  }
}

# Azure OpenAI Service
resource "azurerm_cognitive_account" "scout_platform_openai" {
  name                = var.openai_service_name
  location           = azurerm_resource_group.scout_platform.location
  resource_group_name = azurerm_resource_group.scout_platform.name
  kind               = "OpenAI"
  sku_name           = "S0"

  tags = {
    Environment = var.environment
    Project     = "scout-platform"
  }
}

# Azure OpenAI Deployment - GPT-4
resource "azurerm_cognitive_deployment" "gpt4" {
  name                 = "gpt-4"
  cognitive_account_id = azurerm_cognitive_account.scout_platform_openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4"
    version = "0613"
  }

  scale {
    type = "Standard"
  }
}

# Azure OpenAI Deployment - Text Embedding
resource "azurerm_cognitive_deployment" "text_embedding" {
  name                 = "text-embedding-ada-002"
  cognitive_account_id = azurerm_cognitive_account.scout_platform_openai.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-ada-002"
    version = "2"
  }

  scale {
    type = "Standard"
  }
}