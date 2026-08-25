output "registry_container_app_name" {
  value = azurerm_container_app.registry.name
}

output "registry_identity_principal_id" {
  value = azurerm_container_app.registry.identity[0].principal_id
}

output "registry_latest_revision_name" {
  value = azurerm_container_app.registry.latest_revision_name
}

output "registry_fqdn" {
  value = azurerm_container_app.registry.latest_revision_fqdn
}
