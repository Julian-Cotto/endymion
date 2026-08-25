output "bootstrap_container_app_name" {
  value = azurerm_container_app.bootstrap.name
}

output "bootstrap_fqdn" {
  value = azurerm_container_app.bootstrap.latest_revision_fqdn
}

output "bootstrap_principal_id" {
  value = azurerm_container_app.bootstrap.identity[0].principal_id
}
