# ==============================================================
# MSME Financial Health Card — Terraform Root Module (GCP)
# ==============================================================
# Provider: Google Cloud Platform
# Stage: 1 (GCP-first; AWS-portable design via adapter pattern)
# Region: asia-south1 (Mumbai) — closest to IDBI's target geography
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

  # Remote state backend — configure before first apply
  # Uncomment and fill in your GCS bucket for remote state:
  # backend "gcs" {
  #   bucket = "msme-healthcard-tfstate"
  #   prefix = "terraform/state"
  # }
}

# ---- Provider Configuration ----

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# ---- Enable Required GCP APIs ----

resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",            # Cloud Run
    "sql-component.googleapis.com",  # Cloud SQL
    "sqladmin.googleapis.com",       # Cloud SQL Admin
    "secretmanager.googleapis.com",  # Secret Manager
    "pubsub.googleapis.com",         # Pub/Sub
    "storage.googleapis.com",        # Cloud Storage
    "artifactregistry.googleapis.com", # Container registry
    "cloudarmor.googleapis.com",     # Cloud Armor / WAF
    "vpcaccess.googleapis.com",      # Serverless VPC Access
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# ---- VPC & Networking Module ----

module "network" {
  source = "../../modules/network"

  project_id   = var.project_id
  region       = var.region
  environment  = var.environment
  network_name = "${var.app_name}-${var.environment}-vpc"

  depends_on = [google_project_service.required_apis]
}

# ---- Cloud Storage (Data Lake for synthetic/raw data) ----

module "storage" {
  source = "../../modules/storage"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  app_name    = var.app_name

  depends_on = [google_project_service.required_apis]
}

# ---- Secret Manager ----

module "secrets" {
  source = "../../modules/secrets"

  project_id   = var.project_id
  region       = var.region
  environment  = var.environment
  app_name     = var.app_name

  # Initial secret values — rotate after first deploy
  jwt_secret          = var.jwt_secret
  db_password         = module.cloud_sql.db_password
  backend_service_url = module.backend_cloud_run.service_url

  depends_on = [google_project_service.required_apis]
}

# ---- Cloud SQL (Postgres 15) ----

module "cloud_sql" {
  source = "../../modules/cloud_sql"

  project_id   = var.project_id
  region       = var.region
  environment  = var.environment
  app_name     = var.app_name

  database_version = "POSTGRES_15"
  tier             = var.db_tier
  db_name          = "${var.app_name}_${var.environment}"
  db_user          = "${var.app_name}_app"

  private_network = module.network.vpc_id

  depends_on = [
    google_project_service.required_apis,
    module.network,
  ]
}

# ---- Pub/Sub (Event-driven rescoring) ----

module "pubsub" {
  source = "../../modules/pubsub"

  project_id  = var.project_id
  environment = var.environment
  app_name    = var.app_name

  topics = [
    {
      name                       = "rescore-events"
      message_retention_duration = "86400s" # 1 day
    },
    {
      name                       = "audit-events"
      message_retention_duration = "604800s" # 7 days
    }
  ]

  depends_on = [google_project_service.required_apis]
}

# ---- Artifact Registry (Container images) ----

resource "google_artifact_registry_repository" "containers" {
  provider = google-beta

  location      = var.region
  repository_id = "${var.app_name}-images"
  description   = "Container images for MSME Financial Health Card services"
  format        = "DOCKER"

  labels = {
    environment = var.environment
    app         = var.app_name
    managed_by  = "terraform"
  }

  depends_on = [google_project_service.required_apis]
}

# ---- Backend Cloud Run Service ----

module "backend_cloud_run" {
  source = "../../modules/cloud_run"

  project_id    = var.project_id
  region        = var.region
  environment   = var.environment
  service_name  = "${var.app_name}-backend"
  image         = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.containers.repository_id}/backend:latest"
  port          = 8000
  app_name      = var.app_name

  min_instances = var.backend_min_instances
  max_instances = var.backend_max_instances
  cpu_limit     = "2"
  memory_limit  = "2Gi"

  vpc_connector = module.network.vpc_connector_id

  environment_variables = {
    APP_ENV          = var.environment
    CLOUD_PROVIDER   = "gcp"
    GCP_PROJECT_ID   = var.project_id
    GCP_REGION       = var.region
    POSTGRES_DB      = module.cloud_sql.database_name
    POSTGRES_USER    = module.cloud_sql.database_user
    POSTGRES_HOST    = module.cloud_sql.private_ip_address
    POSTGRES_PORT    = "5432"
    GCS_BUCKET_NAME  = module.storage.synthetic_data_bucket_name
    PUBSUB_TOPIC_RESCORE = module.pubsub.topic_ids["rescore-events"]
    APP_LOG_LEVEL    = "INFO"
  }

  secret_environment_variables = {
    POSTGRES_PASSWORD = {
      secret  = module.secrets.secret_ids["db-password"]
      version = "latest"
    }
    JWT_SECRET_KEY = {
      secret  = module.secrets.secret_ids["jwt-secret"]
      version = "latest"
    }
  }

  depends_on = [
    google_artifact_registry_repository.containers,
    module.cloud_sql,
    module.secrets,
    module.pubsub,
    module.network,
  ]
}

# ---- Frontend Cloud Run Service ----

module "frontend_cloud_run" {
  source = "../../modules/cloud_run"

  project_id    = var.project_id
  region        = var.region
  environment   = var.environment
  service_name  = "${var.app_name}-frontend"
  image         = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.containers.repository_id}/frontend:latest"
  port          = 80
  app_name      = var.app_name

  min_instances = var.frontend_min_instances
  max_instances = var.frontend_max_instances
  cpu_limit     = "1"
  memory_limit  = "512Mi"

  # Frontend is public-facing — no VPC connector needed
  vpc_connector = null

  environment_variables = {
    NGINX_PORT = "80"
  }

  secret_environment_variables = {}

  # Allow unauthenticated access (CORS + API key enforced at backend)
  allow_public_access = true

  depends_on = [
    google_artifact_registry_repository.containers,
    module.backend_cloud_run,
  ]
}

# ---- Cloud Armor (WAF) — protect backend ----

resource "google_compute_security_policy" "backend_waf" {
  name    = "${var.app_name}-${var.environment}-waf"
  project = var.project_id

  description = "Cloud Armor WAF policy for MSME Health Card backend"

  # Rule 1: Block known malicious IPs (preconfigured rules)
  rule {
    action   = "deny(403)"
    priority = "1000"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-stable')"
      }
    }
    description = "Block XSS attacks"
  }

  rule {
    action   = "deny(403)"
    priority = "1001"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-stable')"
      }
    }
    description = "Block SQL injection attacks"
  }

  # Rule 2: Rate limiting (per IP)
  rule {
    action   = "throttle"
    priority = "2000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
    }
    description = "Rate limit: 100 requests/minute per IP"
  }

  # Default rule — allow all other traffic
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }

  depends_on = [google_project_service.required_apis]
}
