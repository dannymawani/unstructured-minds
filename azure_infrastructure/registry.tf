# Azure Container Registry — Basic (free for 12 months)
resource "azurerm_container_registry" "main" {
  name                = "umcontainerreg"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false

  tags = {
    project    = var.project_name
    managed_by = "terraform"
    tier       = "free-12mo"
  }
}

# Allow the Container App's managed identity to pull images
resource "azurerm_role_assignment" "backend_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.backend.identity[0].principal_id
}
