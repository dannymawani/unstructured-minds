resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}"
  location = var.location

  tags = {
    project     = var.project_name
    environment = "production"
    managed_by  = "terraform"
  }
}
