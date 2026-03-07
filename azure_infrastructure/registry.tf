# Azure Container Registry — Basic (free for 12 months)
resource "azurerm_container_registry" "main" {
  name                = "umcontainerreg"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = {
    project    = var.project_name
    managed_by = "terraform"
    tier       = "free-12mo"
  }
}
