# ==============================================================
# Module: cloud_run — Reusable Cloud Run service
# ==============================================================

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "service_name" { type = string }
variable "image" { type = string }
variable "port" { type = number }
variable "app_name" { type = string }
variable "min_instances" { type = number; default = 0 }
variable "max_instances" { type = number; default = 5 }
variable "cpu_limit" { type = string; default = "1" }
variable "memory_limit" { type = string; default = "512Mi" }
variable "vpc_connector" { type = string; default = null }
variable "allow_public_access" { type = bool; default = false }

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "secret_environment_variables" {
  type = map(object({
    secret  = string
    version = string
  }))
  default = {}
}
