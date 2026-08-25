locals {
  app_name = "${var.name_prefix}-shell-bootstrap-${var.environment}"
}

resource "azurerm_container_app" "bootstrap" {
  name                         = local.app_name
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_apps_environment_id
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  registry {
    server   = var.acr_login_server
    identity = "system"
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 2

    container {
      name   = "bootstrap"
      image  = "${var.acr_login_server}/${var.image_name}:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "APP_ENV"
        value = var.environment
      }

      env {
        name  = "APP_CONFIGURATION_ENDPOINT"
        value = var.app_configuration_endpoint
      }

      env {
        name  = "APP_CONFIGURATION_LABEL"
        value = var.environment
      }

      env {
        name  = "REGISTRY_URL"
        value = var.registry_url
      }

      env {
        name  = "REGISTRY_AUDIENCE"
        value = var.registry_audience
      }

      env {
        name  = "ENTRA_TENANT_ID"
        value = var.entra_tenant_id
      }

      env {
        name  = "ENTRA_AUDIENCE"
        value = var.entra_audience
      }

      env {
        name  = "ENTRA_ISSUER"
        value = var.entra_issuer
      }

      env {
        name  = "CACHE_BACKEND"
        value = var.cache_backend
      }

      env {
        name  = "CACHE_TTL_SECONDS"
        value = "30"
      }

      env {
        name  = "REDIS_URL"
        value = var.redis_url
      }

      env {
        name  = "BOOTSTRAP_INCLUDE_FLAG_PREFIXES"
        value = var.bootstrap_include_flag_prefixes
      }

      env {
        name  = "CORS_ALLOW_ORIGINS"
        value = var.cors_allow_origins
      }
    }
  }
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.bootstrap.identity[0].principal_id
}

resource "azurerm_role_assignment" "app_config_reader" {
  scope                = var.app_configuration_id
  role_definition_name = "App Configuration Data Reader"
  principal_id         = azurerm_container_app.bootstrap.identity[0].principal_id
}
