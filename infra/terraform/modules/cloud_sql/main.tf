# ==============================================================
# Module: cloud_sql — Postgres 15 on Cloud SQL
# ==============================================================

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "app_name" { type = string }
variable "database_version" { type = string; default = "POSTGRES_15" }
variable "tier" { type = string; default = "db-f1-micro" }
variable "db_name" { type = string }
variable "db_user" { type = string }
variable "private_network" { type = string }

resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "google_sql_database_instance" "postgres" {
  name             = "${var.app_name}-${var.environment}-pg"
  database_version = var.database_version
  region           = var.region
  project          = var.project_id

  settings {
    tier              = var.tier
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    disk_autoresize   = true
    disk_size         = 20 # GB — starts small; autoresize handles growth

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = var.environment == "prod"
      backup_retention_settings {
        retained_backups = var.environment == "prod" ? 30 : 7
      }
    }

    ip_configuration {
      ipv4_enabled    = false # Private IP only — no public exposure
      private_network = var.private_network
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }

    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = false # Privacy — do not log client IPs
    }

    user_labels = {
      environment = var.environment
      app         = var.app_name
      managed_by  = "terraform"
    }
  }

  deletion_protection = var.environment == "prod"

  lifecycle {
    prevent_destroy = false
  }
}

resource "google_sql_database" "app_db" {
  name     = var.db_name
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

resource "google_sql_user" "app_user" {
  name     = var.db_user
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
  project  = var.project_id
}

output "connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "private_ip_address" {
  value     = google_sql_database_instance.postgres.private_ip_address
  sensitive = true
}

output "database_name" {
  value = google_sql_database.app_db.name
}

output "database_user" {
  value = google_sql_user.app_user.name
}

output "db_password" {
  value     = random_password.db_password.result
  sensitive = true
}
