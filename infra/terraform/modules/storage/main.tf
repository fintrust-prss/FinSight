# ==============================================================
# Module: storage — GCS Buckets
# ==============================================================

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "app_name" { type = string }

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# ---- Synthetic / Raw Data Lake bucket ----

resource "google_storage_bucket" "synthetic_data" {
  name          = "${var.app_name}-${var.environment}-synthetic-${random_id.bucket_suffix.hex}"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  # Versioning: keep previous versions for audit/replay
  versioning {
    enabled = true
  }

  # Lifecycle: transition old data to cheaper storage after 90 days
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  # No public access — all access goes via backend service
  uniform_bucket_level_access = true

  cors {
    origin          = ["*"]
    method          = ["GET"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }

  labels = {
    environment = var.environment
    app         = var.app_name
    managed_by  = "terraform"
    data_class  = "synthetic"
  }
}

# ---- ML Model Artifacts bucket ----

resource "google_storage_bucket" "model_artifacts" {
  name          = "${var.app_name}-${var.environment}-models-${random_id.bucket_suffix.hex}"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  versioning {
    enabled = true
  }

  uniform_bucket_level_access = true

  labels = {
    environment = var.environment
    app         = var.app_name
    managed_by  = "terraform"
    data_class  = "model-artifacts"
  }
}

output "synthetic_data_bucket_name" {
  description = "GCS bucket for synthetic raw data lake."
  value       = google_storage_bucket.synthetic_data.name
}

output "model_artifacts_bucket_name" {
  description = "GCS bucket for ML model artifacts (joblib/ONNX)."
  value       = google_storage_bucket.model_artifacts.name
}
