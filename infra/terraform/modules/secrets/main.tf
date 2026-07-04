# ==============================================================
# Module: secrets — Secret Manager resources
# ==============================================================

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "app_name" { type = string }
variable "jwt_secret" { type = string; sensitive = true }
variable "db_password" { type = string; sensitive = true }
variable "backend_service_url" { type = string; default = "" }

locals {
  secrets = {
    "jwt-secret" = var.jwt_secret
    "db-password" = var.db_password
  }
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = local.secrets
  project   = var.project_id
  secret_id = "${var.app_name}-${var.environment}-${each.key}"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    environment = var.environment
    app         = var.app_name
    managed_by  = "terraform"
  }
}

resource "google_secret_manager_secret_version" "versions" {
  for_each    = local.secrets
  secret      = google_secret_manager_secret.secrets[each.key].id
  secret_data = each.value
}

output "secret_ids" {
  description = "Map of secret name to Secret Manager secret ID."
  value       = { for k, s in google_secret_manager_secret.secrets : k => s.secret_id }
  sensitive   = true
}
