# Azure Static Web Apps — Free (always free)
resource "azurerm_static_web_app" "frontend" {
  name                = "um-frontend"
  resource_group_name = azurerm_resource_group.main.name
  location            = "westeurope" # SWA has limited region availability
  sku_tier            = "Free"
  sku_size            = "Free"

  tags = {
    project    = var.project_name
    managed_by = "terraform"
    tier       = "free"
  }
}
