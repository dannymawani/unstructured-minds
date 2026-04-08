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

  template {
    min_replicas = 0 # Scale to zero when idle
    max_replicas = 2

    container {
      name   = "backend"
      image  = "${azurerm_container_registry.main.login_server}/um-backend:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
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
    name  = "database-url"
    value = "postgresql://umadmin:${var.postgres_admin_password}@${azurerm_postgresql_flexible_server.main.fqdn}/unstructured_minds?sslmode=require"
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
