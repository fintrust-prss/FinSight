# ==============================================================
# Module: network — VPC + Serverless VPC Access Connector
# ==============================================================

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "network_name" { type = string }

# ---- VPC Network ----

resource "google_compute_network" "vpc" {
  name                    = var.network_name
  auto_create_subnetworks = false
  project                 = var.project_id
}

# ---- Subnet for Cloud Run VPC Connector ----

resource "google_compute_subnetwork" "connector_subnet" {
  name          = "${var.network_name}-connector-subnet"
  ip_cidr_range = "10.8.0.0/28" # /28 = 14 usable IPs — required minimum for connectors
  region        = var.region
  network       = google_compute_network.vpc.id
  project       = var.project_id

  private_ip_google_access = true # Allow access to Google APIs without public IP
}

# ---- Subnet for Cloud SQL private IP ----

resource "google_compute_subnetwork" "sql_subnet" {
  name          = "${var.network_name}-sql-subnet"
  ip_cidr_range = "10.9.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
  project       = var.project_id

  private_ip_google_access = true
}

# ---- Private Service Connection (for Cloud SQL private IP) ----

resource "google_compute_global_address" "sql_private_ip_range" {
  name          = "${var.network_name}-sql-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
  project       = var.project_id
}

resource "google_service_networking_connection" "sql_private_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.sql_private_ip_range.name]
}

# ---- Serverless VPC Access Connector (Cloud Run → VPC → Cloud SQL) ----

resource "google_vpc_access_connector" "connector" {
  name          = "${var.environment}-connector"
  region        = var.region
  project       = var.project_id
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28"

  min_throughput = 200 # Mbps
  max_throughput = 1000

  depends_on = [google_compute_subnetwork.connector_subnet]
}

output "vpc_id" {
  value = google_compute_network.vpc.id
}

output "vpc_name" {
  value = google_compute_network.vpc.name
}

output "vpc_connector_id" {
  value = google_vpc_access_connector.connector.id
}
