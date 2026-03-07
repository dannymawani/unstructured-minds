output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "postgres_connection_string" {
  value     = "postgresql://umadmin:${var.postgres_admin_password}@${azurerm_postgresql_flexible_server.main.fqdn}/unstructured_minds?sslmode=require"
  sensitive = true
}

output "container_registry_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "backend_url" {
  value = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}

output "frontend_url" {
  value = "https://${azurerm_static_web_app.frontend.default_host_name}"
}

output "github_actions_client_id" {
  value = azuread_application.github_actions.client_id
}
