# Example of consuming outputs from the shared platform/common infrastructure repository.
# Replace backend details with your actual shared state location.

data "terraform_remote_state" "platform" {
  backend = "azurerm"

  config = {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "stplatformtfstate"
    container_name       = "tfstate"
    key                  = "platform/${var.environment}.tfstate"
  }
}

# Optional: use shared outputs instead of explicit variables if desired.
# locals {
#   container_apps_environment_id = data.terraform_remote_state.platform.outputs.container_apps_environment_id
#   acr_id                        = data.terraform_remote_state.platform.outputs.acr_id
#   acr_login_server              = data.terraform_remote_state.platform.outputs.acr_login_server
# }
