variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
  default     = "scout-platform-rg"
}

variable "acr_name" {
  description = "Azure Container Registry name"
  type        = string
  default     = "scoutplatformacr"
}

variable "aks_cluster_name" {
  description = "AKS cluster name"
  type        = string
  default     = "scout-platform-aks"
}

variable "aks_node_count" {
  description = "Number of AKS nodes"
  type        = number
  default     = 2
}

variable "aks_vm_size" {
  description = "AKS VM size"
  type        = string
  default     = "Standard_B2s"
}

variable "static_web_app_name" {
  description = "Static Web App name"
  type        = string
  default     = "scout-platform-webapp"
}

variable "postgresql_server_name" {
  description = "PostgreSQL server name"
  type        = string
  default     = "scout-platform-postgres"
}

variable "postgresql_admin_username" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "scout_admin"
  sensitive   = true
}

variable "postgresql_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "redis_cache_name" {
  description = "Redis cache name"
  type        = string
  default     = "scout-platform-redis"
}

variable "openai_service_name" {
  description = "Azure OpenAI service name"
  type        = string
  default     = "scout-platform-openai"
}