resource "azurerm_container_app" "registry" {
  name                         = local.registry_app_name
  container_app_environment_id = var.container_apps_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = var.acr_login_server
    identity = "system"
  }

  template {
    min_replicas = 1
    max_replicas = 2

    container {
      name   = "registry"
      image  = "${var.acr_login_server}/${var.registry_image_name}:${var.registry_image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }

      env {
        name  = "ENVIRONMENT_NAME"
        value = var.environment
      }

      env {
        name  = "ALLOWED_FRONTEND_HOSTS"
        value = var.allowed_frontend_hosts
      }

      env {
        name  = "ALLOWED_API_HOSTS"
        value = var.allowed_api_hosts
      }

      env {
        name  = "SHELL_READ_AUDIENCES"
        value = var.shell_read_audiences
      }

      env {
        name  = "PIPELINE_WRITE_AUDIENCES"
        value = var.pipeline_write_audiences
      }

      env {
        name  = "AUTH_DISABLED"
        value = "false"
      }
    }
  }
}
