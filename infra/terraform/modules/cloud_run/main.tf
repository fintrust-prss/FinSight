# ==============================================================
# Module: cloud_run — Cloud Run service resource
# ==============================================================

resource "google_cloud_run_v2_service" "service" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    dynamic "vpc_access" {
      for_each = var.vpc_connector != null ? [1] : []
      content {
        connector = var.vpc_connector
        egress    = "PRIVATE_RANGES_ONLY"
      }
    }

    containers {
      image = var.image

      ports {
        container_port = var.port
      }

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
        cpu_idle = true # Allow CPU throttling when idle (cost saving)
      }

      # Plain environment variables
      dynamic "env" {
        for_each = var.environment_variables
        content {
          name  = env.key
          value = env.value
        }
      }

      # Secret-backed environment variables
      dynamic "env" {
        for_each = var.secret_environment_variables
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value.secret
              version = env.value.version
            }
          }
        }
      }

      # Liveness probe (maps to /healthz)
      liveness_probe {
        http_get {
          path = "/healthz"
          port = var.port
        }
        initial_delay_seconds = 15
        timeout_seconds       = 5
        failure_threshold     = 3
      }

      # Startup probe (give extra time on cold start)
      startup_probe {
        http_get {
          path = "/healthz"
          port = var.port
        }
        initial_delay_seconds = 5
        timeout_seconds       = 5
        failure_threshold     = 10
        period_seconds        = 3
      }
    }

    labels = {
      environment = var.environment
      app         = var.app_name
      managed_by  = "terraform"
    }
  }

  labels = {
    environment = var.environment
    app         = var.app_name
    managed_by  = "terraform"
  }

  lifecycle {
    ignore_changes = [
      # Image is updated by CI/CD, not Terraform
      template[0].containers[0].image,
    ]
  }
}

# ---- IAM: Allow public access if specified ----

resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count = var.allow_public_access ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
