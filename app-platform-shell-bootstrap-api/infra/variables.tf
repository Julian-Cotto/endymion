variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "container_apps_environment_id" {
  type = string
}

variable "acr_id" {
  type = string
}

variable "acr_login_server" {
  type = string
}

variable "registry_url" {
  type = string
}

variable "app_configuration_endpoint" {
  type = string
}

variable "app_configuration_id" {
  type = string
}

variable "image_name" {
  type    = string
  default = "shell-bootstrap-api"
}

variable "image_tag" {
  type = string
}

variable "name_prefix" {
  type = string
}

variable "environment" {
  type = string
}

variable "entra_tenant_id" {
  type = string
}

variable "entra_audience" {
  type = string
}

variable "entra_issuer" {
  type = string
}

variable "registry_audience" {
  type    = string
  default = "api://portal-registry-runtime/.default"
}

variable "cache_backend" {
  type    = string
  default = "memory"
}

variable "redis_url" {
  type    = string
  default = ""
}

variable "bootstrap_include_flag_prefixes" {
  type    = string
  default = "shell.,orders.,inventory.,billing."
}

variable "cors_allow_origins" {
  type    = string
  default = "http://localhost:5173"
}
