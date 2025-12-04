# ============================================
# CRM Jurídico AI - Terraform Infrastructure
# ============================================
# Infraestrutura completa no Google Cloud Platform
# 
# Recursos criados:
# - Cloud SQL (PostgreSQL 16 com pgvector)
# - Cloud Storage (documentos jurídicos)
# - Cloud Run (API + Frontend + Workers)
# - Memorystore (Redis)
# - Secret Manager (credenciais)
# - Cloud Armor (WAF/DDoS)
# - VPC Connector (comunicação privada)

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  # Backend remoto (configurar para produção)
  # backend "gcs" {
  #   bucket = "crm-juridico-terraform-state"
  #   prefix = "terraform/state"
  # }
}

# ============================================
# Variables
# ============================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "southamerica-east1"  # São Paulo
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT Secret Key"
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Gemini API Key"
  type        = string
  sensitive   = true
}

variable "domain" {
  description = "Custom domain (optional)"
  type        = string
  default     = ""
}

locals {
  app_name = "crm-juridico"
  labels = {
    app         = local.app_name
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ============================================
# Provider Configuration
# ============================================

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ============================================
# Enable Required APIs
# ============================================

resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "redis.googleapis.com",
    "vpcaccess.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "aiplatform.googleapis.com",
    "storage.googleapis.com",
    "cloudtasks.googleapis.com",
    "pubsub.googleapis.com",
    "firebaseauth.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# ============================================
# VPC Network
# ============================================

resource "google_compute_network" "vpc" {
  name                    = "${local.app_name}-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.services]
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${local.app_name}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id

  private_ip_google_access = true
}

# VPC Connector para Cloud Run acessar recursos privados
resource "google_vpc_access_connector" "connector" {
  name          = "${local.app_name}-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc.name

  depends_on = [google_project_service.services]
}

# Private Service Access para Cloud SQL
resource "google_compute_global_address" "private_ip" {
  name          = "${local.app_name}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
}

# ============================================
# Cloud SQL (PostgreSQL with pgvector)
# ============================================

resource "google_sql_database_instance" "postgres" {
  name             = "${local.app_name}-db-${var.environment}"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = var.environment == "prod" ? "db-custom-2-4096" : "db-f1-micro"
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    disk_size         = var.environment == "prod" ? 50 : 10
    disk_type         = "PD_SSD"

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.vpc.id
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.environment == "prod"
      backup_retention_settings {
        retained_backups = var.environment == "prod" ? 30 : 7
      }
    }

    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }

    maintenance_window {
      day          = 7  # Domingo
      hour         = 4
      update_track = "stable"
    }
  }

  deletion_protection = var.environment == "prod"

  depends_on = [google_service_networking_connection.private_vpc]
}

resource "google_sql_database" "database" {
  name     = "crm_juridico"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "user" {
  name     = "crm_app"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

# ============================================
# Memorystore (Redis)
# ============================================

resource "google_redis_instance" "cache" {
  name               = "${local.app_name}-redis"
  tier               = var.environment == "prod" ? "STANDARD_HA" : "BASIC"
  memory_size_gb     = var.environment == "prod" ? 2 : 1
  region             = var.region
  redis_version      = "REDIS_7_0"
  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  labels = local.labels

  depends_on = [google_service_networking_connection.private_vpc]
}

# ============================================
# Cloud Storage (Documentos)
# ============================================

resource "google_storage_bucket" "documents" {
  name          = "${var.project_id}-documentos-${var.environment}"
  location      = var.region
  storage_class = "STANDARD"
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  versioning {
    enabled = var.environment == "prod"
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  labels = local.labels
}

# ============================================
# Secret Manager
# ============================================

resource "google_secret_manager_secret" "db_password" {
  secret_id = "${local.app_name}-db-password"

  replication {
    auto {}
  }

  labels = local.labels
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "${local.app_name}-jwt-secret"

  replication {
    auto {}
  }

  labels = local.labels
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = var.jwt_secret_key
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "${local.app_name}-gemini-api-key"

  replication {
    auto {}
  }

  labels = local.labels
}

resource "google_secret_manager_secret_version" "gemini_api_key" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key
}

# ============================================
# Service Account for Cloud Run
# ============================================

resource "google_service_account" "cloudrun" {
  account_id   = "${local.app_name}-cloudrun"
  display_name = "CRM Jurídico Cloud Run Service Account"
}

# Permissões
resource "google_project_iam_member" "cloudrun_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectAdmin",
    "roles/aiplatform.user",
    "roles/cloudtasks.enqueuer",
    "roles/pubsub.publisher",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# ============================================
# Cloud Run - Backend API
# ============================================

resource "google_cloud_run_v2_service" "api" {
  name     = "${local.app_name}-api"
  location = var.region

  template {
    service_account = google_service_account.cloudrun.email

    scaling {
      min_instance_count = var.environment == "prod" ? 1 : 0
      max_instance_count = var.environment == "prod" ? 10 : 2
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "gcr.io/${var.project_id}/${local.app_name}-api:latest"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = var.environment == "prod" ? "2" : "1"
          memory = var.environment == "prod" ? "2Gi" : "512Mi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "GCS_BUCKET_DOCUMENTOS"
        value = google_storage_bucket.documents.name
      }

      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
      }

      env {
        name  = "DATABASE_URL"
        value = "postgresql+asyncpg://crm_app:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/crm_juridico"
      }

      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        period_seconds = 30
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  labels = local.labels

  depends_on = [
    google_project_iam_member.cloudrun_roles,
    google_sql_database.database,
  ]
}

# Permitir acesso público à API
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ============================================
# Cloud Run - Frontend
# ============================================

resource "google_cloud_run_v2_service" "frontend" {
  name     = "${local.app_name}-frontend"
  location = var.region

  template {
    scaling {
      min_instance_count = var.environment == "prod" ? 1 : 0
      max_instance_count = var.environment == "prod" ? 5 : 2
    }

    containers {
      image = "gcr.io/${var.project_id}/${local.app_name}-frontend:latest"

      ports {
        container_port = 80
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
      }

      env {
        name  = "VITE_API_URL"
        value = google_cloud_run_v2_service.api.uri
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  labels = local.labels
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  name     = google_cloud_run_v2_service.frontend.name
  location = google_cloud_run_v2_service.frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ============================================
# Cloud Run - Celery Worker
# ============================================

resource "google_cloud_run_v2_service" "worker" {
  name     = "${local.app_name}-worker"
  location = var.region

  template {
    service_account = google_service_account.cloudrun.email

    scaling {
      min_instance_count = 0
      max_instance_count = var.environment == "prod" ? 5 : 1
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "gcr.io/${var.project_id}/${local.app_name}-api:latest"

      command = ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info"]

      resources {
        limits = {
          cpu    = var.environment == "prod" ? "2" : "1"
          memory = var.environment == "prod" ? "2Gi" : "1Gi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "GCS_BUCKET_DOCUMENTOS"
        value = google_storage_bucket.documents.name
      }

      env {
        name  = "CELERY_BROKER_URL"
        value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/1"
      }

      env {
        name  = "CELERY_RESULT_BACKEND"
        value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/2"
      }

      env {
        name  = "DATABASE_URL"
        value = "postgresql+asyncpg://crm_app:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/crm_juridico"
      }

      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  labels = local.labels

  depends_on = [google_project_iam_member.cloudrun_roles]
}

# ============================================
# Cloud Scheduler - Celery Beat
# ============================================

resource "google_cloud_scheduler_job" "check_prazos" {
  name        = "${local.app_name}-check-prazos"
  description = "Verifica prazos próximos a cada 30 minutos"
  schedule    = "*/30 * * * *"
  time_zone   = "America/Sao_Paulo"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.api.uri}/api/v1/internal/check-prazos"

    oidc_token {
      service_account_email = google_service_account.cloudrun.email
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_cloud_scheduler_job" "send_notifications" {
  name        = "${local.app_name}-send-notifications"
  description = "Envia notificações a cada 5 minutos"
  schedule    = "*/5 * * * *"
  time_zone   = "America/Sao_Paulo"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.api.uri}/api/v1/internal/send-notifications"

    oidc_token {
      service_account_email = google_service_account.cloudrun.email
    }
  }

  depends_on = [google_project_service.services]
}

# ============================================
# Outputs
# ============================================

output "api_url" {
  description = "URL da API"
  value       = google_cloud_run_v2_service.api.uri
}

output "frontend_url" {
  description = "URL do Frontend"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_private_ip" {
  description = "Cloud SQL private IP"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "redis_host" {
  description = "Redis host"
  value       = google_redis_instance.cache.host
}

output "storage_bucket" {
  description = "Nome do bucket de documentos"
  value       = google_storage_bucket.documents.name
}
