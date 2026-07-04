# ==============================================================
# MSME Financial Health Card — Terraform Variables
# ==============================================================

# ---- Project & Region ----

variable "project_id" {
  type        = string
  description = "GCP Project ID. Must be pre-created before running Terraform."
}

variable "region" {
  type        = string
  description = "Primary GCP region for all resources."
  default     = "asia-south1" # Mumbai — closest to IDBI geography
}

variable "zone" {
  type        = string
  description = "GCP zone (used for zonal resources like Cloud SQL)."
  default     = "asia-south1-a"
}

variable "environment" {
  type        = string
  description = "Deployment environment: dev | staging | prod"
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod"
  }
}

variable "app_name" {
  type        = string
  description = "Short application name used as prefix for all resource names."
  default     = "msme-healthcard"
}

# ---- Database ----

variable "db_tier" {
  type        = string
  description = "Cloud SQL machine type (tier). e.g. db-f1-micro (dev), db-g1-small (staging), db-n1-standard-2 (prod)"
  default     = "db-f1-micro"
}

# ---- Cloud Run: Backend ----

variable "backend_min_instances" {
  type        = number
  description = "Minimum Cloud Run instances for backend (0 = scale-to-zero in dev)."
  default     = 0
}

variable "backend_max_instances" {
  type        = number
  description = "Maximum Cloud Run instances for backend."
  default     = 5
}

# ---- Cloud Run: Frontend ----

variable "frontend_min_instances" {
  type        = number
  description = "Minimum Cloud Run instances for frontend (0 = scale-to-zero in dev)."
  default     = 0
}

variable "frontend_max_instances" {
  type        = number
  description = "Maximum Cloud Run instances for frontend."
  default     = 3
}

# ---- Secrets (sensitive — always pass via tfvars or CI secrets, never hardcode) ----

variable "jwt_secret" {
  type        = string
  description = "JWT signing secret. Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
  sensitive   = true
}

# ---- Labels / Tags ----

variable "labels" {
  type        = map(string)
  description = "Common labels applied to all GCP resources."
  default = {
    managed_by  = "terraform"
    app         = "msme-healthcard"
    team        = "idbi-hackathon"
    cost_center = "hackathon"
  }
}
