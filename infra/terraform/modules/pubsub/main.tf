# ==============================================================
# Module: pubsub — Pub/Sub topics + subscriptions
# ==============================================================

variable "project_id" { type = string }
variable "environment" { type = string }
variable "app_name" { type = string }

variable "topics" {
  type = list(object({
    name                       = string
    message_retention_duration = string
  }))
  description = "List of Pub/Sub topics to create."
}

# ---- Create topics ----

resource "google_pubsub_topic" "topics" {
  for_each = { for t in var.topics : t.name => t }

  name    = "${var.app_name}-${var.environment}-${each.key}"
  project = var.project_id

  message_retention_duration = each.value.message_retention_duration

  labels = {
    environment = var.environment
    app         = var.app_name
    managed_by  = "terraform"
  }
}

# ---- Create push subscriptions (backend worker) ----

resource "google_pubsub_subscription" "subscriptions" {
  for_each = { for t in var.topics : t.name => t }

  name    = "${var.app_name}-${var.environment}-${each.key}-sub"
  topic   = google_pubsub_topic.topics[each.key].name
  project = var.project_id

  ack_deadline_seconds = 60

  # Retry policy — exponential backoff
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }

  # Dead-letter policy for unprocessable messages
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }

  message_retention_duration = each.value.message_retention_duration

  labels = {
    environment = var.environment
    app         = var.app_name
    managed_by  = "terraform"
  }
}

# ---- Dead-letter topic ----

resource "google_pubsub_topic" "dead_letter" {
  name    = "${var.app_name}-${var.environment}-dead-letter"
  project = var.project_id

  labels = {
    environment = var.environment
    app         = var.app_name
    managed_by  = "terraform"
  }
}

output "topic_ids" {
  description = "Map of topic name to Pub/Sub topic ID."
  value       = { for k, t in google_pubsub_topic.topics : k => t.id }
}

output "subscription_ids" {
  description = "Map of topic name to Pub/Sub subscription ID."
  value       = { for k, s in google_pubsub_subscription.subscriptions : k => s.id }
}
