resource "azurerm_role_assignment" "registry_acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.registry.identity[0].principal_id
}
