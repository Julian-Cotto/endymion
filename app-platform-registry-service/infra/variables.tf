variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "environment" {
  type = string
}

variable "name_prefix" {
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

variable "registry_image_name" {
  type    = string
  default = "portal-registry"
}

variable "registry_image_tag" {
  type = string
}

variable "allowed_frontend_hosts" {
  type = string
}

variable "allowed_api_hosts" {
  type = string
}

variable "shell_read_audiences" {
  type = string
}

variable "pipeline_write_audiences" {
  type = string
}

variable "database_url" {
  type      = string
  sensitive = true
}
