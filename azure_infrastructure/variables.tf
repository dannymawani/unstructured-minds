variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "germanywestcentral"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "unstructured-minds"
}

# Database
variable "postgres_admin_password" {
  description = "PostgreSQL administrator password"
  type        = string
  sensitive   = true
}

# App secrets (passed to Container Apps)
variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
}

variable "clerk_secret_key" {
  description = "Clerk secret key"
  type        = string
  sensitive   = true
}

variable "clerk_domain" {
  description = "Clerk domain"
  type        = string
}

variable "clerk_publishable_key" {
  description = "Clerk publishable key (for frontend build)"
  type        = string
}

variable "cors_origins" {
  description = "Allowed CORS origins for the backend"
  type        = string
  default     = "https://app.unstructuredminds.com"
}
