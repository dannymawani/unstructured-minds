# Azure PostgreSQL Flexible Server — B1ms (free for 12 months)
resource "azurerm_postgresql_flexible_server" "main" {
  name                = "um-postgres"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku_name            = "B_Standard_B1ms"
  storage_mb          = 32768 # 32 GB (free tier max)
  version             = "16"

  authentication {
    password_auth_enabled         = true # Keep for local dev / migration
    active_directory_auth_enabled = true
    tenant_id                     = data.azuread_client_config.current.tenant_id
  }

  administrator_login    = "umadmin"
  administrator_password = var.postgres_admin_password

  tags = {
    project    = var.project_name
    managed_by = "terraform"
    tier       = "free-12mo"
  }
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "unstructured_minds"
  server_id = azurerm_postgresql_flexible_server.main.id
}

# Entra ID admin — the Container App's managed identity
resource "azurerm_postgresql_flexible_server_active_directory_administrator" "backend" {
  server_name         = azurerm_postgresql_flexible_server.main.name
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azuread_client_config.current.tenant_id
  object_id           = azurerm_container_app.backend.identity[0].principal_id
  principal_name      = "um-backend"
  principal_type      = "ServicePrincipal"
}

# Allow Azure services to connect (required for Container Apps on Consumption plan
# which use shared, unpredictable outbound IPs). Entra ID auth ensures only our
# managed identity can actually authenticate.
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Developer direct access (optional — set developer_ip in tfvars)
resource "azurerm_postgresql_flexible_server_firewall_rule" "developer" {
  count            = var.developer_ip != "" ? 1 : 0
  name             = "AllowDeveloper"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = var.developer_ip
  end_ip_address   = var.developer_ip
}
