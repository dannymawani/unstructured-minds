# DNS configuration
# Uncomment when ready to use Azure DNS instead of Cloudflare.
# Azure DNS is free for the first zone.

# resource "azurerm_dns_zone" "main" {
#   name                = "unstructuredminds.com"
#   resource_group_name = azurerm_resource_group.main.name
#
#   tags = {
#     project    = var.project_name
#     managed_by = "terraform"
#   }
# }
#
# resource "azurerm_dns_cname_record" "app" {
#   name                = "app"
#   zone_name           = azurerm_dns_zone.main.name
#   resource_group_name = azurerm_resource_group.main.name
#   ttl                 = 300
#   record              = azurerm_static_web_app.frontend.default_host_name
# }
#
# resource "azurerm_dns_cname_record" "api" {
#   name                = "api"
#   zone_name           = azurerm_dns_zone.main.name
#   resource_group_name = azurerm_resource_group.main.name
#   ttl                 = 300
#   record              = azurerm_container_app.backend.ingress[0].fqdn
# }
