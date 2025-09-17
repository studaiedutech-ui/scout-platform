output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.scout_platform.name
}

output "acr_login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.scout_platform.login_server
}

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.scout_platform.name
}

output "static_web_app_url" {
  description = "Static Web App default hostname"
  value       = azurerm_static_site.scout_platform.default_host_name
}

output "postgresql_server_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = azurerm_postgresql_flexible_server.scout_platform.fqdn
}

output "redis_hostname" {
  description = "Redis cache hostname"
  value       = azurerm_redis_cache.scout_platform.hostname
}

output "redis_primary_access_key" {
  description = "Redis primary access key"
  value       = azurerm_redis_cache.scout_platform.primary_access_key
  sensitive   = true
}

output "openai_endpoint" {
  description = "Azure OpenAI service endpoint"
  value       = azurerm_cognitive_account.scout_platform_openai.endpoint
}

output "openai_api_key" {
  description = "Azure OpenAI API key"
  value       = azurerm_cognitive_account.scout_platform_openai.primary_access_key
  sensitive   = true
}