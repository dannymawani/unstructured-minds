# Container Apps environment — Consumption (always free)
resource "azurerm_container_app_environment" "main" {
  name                = "um-env"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  tags = {
    project    = var.project_name
    managed_by = "terraform"
    tier       = "free"
  }
}

# Backend Container App
resource "azurerm_container_app" "backend" {
  name                         = "um-backend"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "System"
  }

  template {
    min_replicas = 0 # Scale to zero when idle
    max_replicas = 2

    container {
      name   = "backend"
      image  = "${azurerm_container_registry.main.login_server}/um-backend:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "AZURE_USE_MANAGED_IDENTITY"
        value = "true"
      }
      env {
        name  = "AZURE_POSTGRES_HOST"
        value = azurerm_postgresql_flexible_server.main.fqdn
      }
      env {
        name  = "AZURE_POSTGRES_DB"
        value = "unstructured_minds"
      }
      env {
        name  = "AZURE_POSTGRES_USER"
        value = "um-backend"
      }
      env {
        name        = "ANTHROPIC_API_KEY"
        secret_name = "anthropic-api-key"
      }
      env {
        name        = "CLERK_SECRET_KEY"
        secret_name = "clerk-secret-key"
      }
      env {
        name  = "CLERK_DOMAIN"
        value = var.clerk_domain
      }
      env {
        name  = "USE_CLOUD"
        value = "true"
      }
      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origins
      }

      liveness_probe {
        path      = "/health/live"
        port      = 8000
        transport = "HTTP"
      }

      readiness_probe {
        path      = "/health/ready"
        port      = 8000
        transport = "HTTP"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  secret {
    name  = "anthropic-api-key"
    value = var.anthropic_api_key
  }
  secret {
    name  = "clerk-secret-key"
    value = var.clerk_secret_key
  }

  tags = {
    project    = var.project_name
    managed_by = "terraform"
    tier       = "free"
  }
}
