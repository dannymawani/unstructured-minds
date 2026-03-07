# Azure PostgreSQL Flexible Server — B1ms (free for 12 months)
resource "azurerm_postgresql_flexible_server" "main" {
  name                = "um-postgres"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku_name            = "B_Standard_B1ms"
  storage_mb          = 32768 # 32 GB (free tier max)
  version             = "16"

  authentication {
    password_auth_enabled = true
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

# Allow Azure services to connect
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}
