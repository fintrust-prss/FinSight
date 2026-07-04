# ==============================================================
# MSME Financial Health Card — Dev Environment
# Terraform entry point for development deployments
# ==============================================================

terraform {
  required_version = ">= 1.8.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.30"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Uncomment after creating your state bucket:
  # backend "gcs" {
  #   bucket = "msme-healthcard-tfstate"
  #   prefix = "terraform/state/dev"
  # }
}

module "msme_healthcard" {
  source = "../../"

  project_id  = var.project_id
  region      = "asia-south1"
  zone        = "asia-south1-a"
  environment = "dev"
  app_name    = "msme-healthcard"

  # Dev: smallest possible resources (cost-effective for hackathon)
  db_tier                = "db-f1-micro"
  backend_min_instances  = 0
  backend_max_instances  = 3
  frontend_min_instances = 0
  frontend_max_instances = 2

  # SENSITIVE: pass via TF_VAR_jwt_secret env variable or -var flag
  jwt_secret = var.jwt_secret
}

variable "project_id" {
  type        = string
  description = "GCP Project ID for dev environment."
}

variable "jwt_secret" {
  type      = string
  sensitive = true
}

# Pass through all outputs from root module
output "backend_url" { value = module.msme_healthcard.backend_service_url }
output "frontend_url" { value = module.msme_healthcard.frontend_service_url }
output "synthetic_bucket" { value = module.msme_healthcard.synthetic_data_bucket }
