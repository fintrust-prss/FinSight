# ==============================================================
# MSME Financial Health Card — Terraform Outputs
# ==============================================================

output "backend_service_url" {
  description = "Cloud Run URL for the backend FastAPI service."
  value       = module.backend_cloud_run.service_url
}

output "frontend_service_url" {
  description = "Cloud Run URL for the frontend React application."
  value       = module.frontend_cloud_run.service_url
}

output "database_connection_name" {
  description = "Cloud SQL connection name for use with Cloud SQL Proxy."
  value       = module.cloud_sql.connection_name
}

output "database_private_ip" {
  description = "Private IP address of Cloud SQL instance (accessible within VPC only)."
  value       = module.cloud_sql.private_ip_address
  sensitive   = true
}

output "synthetic_data_bucket" {
  description = "GCS bucket name for synthetic data lake (raw data ingestion)."
  value       = module.storage.synthetic_data_bucket_name
}

output "artifact_registry_url" {
  description = "Artifact Registry URL for container images."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.containers.repository_id}"
}

output "rescore_pubsub_topic" {
  description = "Pub/Sub topic for triggering incremental MSME rescoring events."
  value       = module.pubsub.topic_ids["rescore-events"]
}

output "vpc_network" {
  description = "VPC network name."
  value       = module.network.vpc_name
}

output "waf_policy_name" {
  description = "Cloud Armor WAF security policy name."
  value       = google_compute_security_policy.backend_waf.name
}

output "project_id" {
  description = "GCP project ID (echo back for reference)."
  value       = var.project_id
}

output "region" {
  description = "GCP region (echo back for reference)."
  value       = var.region
}
