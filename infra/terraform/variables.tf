variable "project" {
  description = "Name prefix"
  type        = string
  default     = "mavik-chat"
}

variable "env" {
  description = "Environment (dev/stage/prod)"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "uploads_bucket_name" {
  description = "Override bucket name (must be globally unique). Leave null to auto-generate."
  type        = string
  default     = null
}

variable "cors_allowed_origins" {
  description = "Allowed origins for browser -> S3 POST"
  type        = list(string)
  default     = ["http://127.0.0.1:3000", "http://localhost:3000"]
}
