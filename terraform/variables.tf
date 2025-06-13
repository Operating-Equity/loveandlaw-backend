variable "project_name" {
  description = "Project name"
  type        = string
  default     = "loveandlaw"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "container_image" {
  description = "Docker container image"
  type        = string
}

variable "container_cpu" {
  description = "Container CPU units"
  type        = number
  default     = 1024
}

variable "container_memory" {
  description = "Container memory in MB"
  type        = number
  default     = 2048
}

variable "elasticsearch_endpoint" {
  description = "Elasticsearch endpoint (Elastic Cloud)"
  type        = string
  default     = "https://b202eece25af4ba8a7cc89b05922ac28.us-east-2.aws.elastic-cloud.com:443"
}

# Sensitive variables (set via terraform.tfvars or environment)
variable "groq_api_key" {
  description = "Groq API key"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}

variable "elasticsearch_api_key" {
  description = "Elasticsearch API key"
  type        = string
  sensitive   = true
}

variable "clerk_publishable_key" {
  description = "Clerk publishable key"
  type        = string
}

variable "clerk_secret_key" {
  description = "Clerk secret key"
  type        = string
  sensitive   = true
}

variable "clerk_frontend_api" {
  description = "Clerk frontend API domain"
  type        = string
}

variable "alert_email" {
  description = "Email address for CloudWatch alerts"
  type        = string
  default     = "admin@loveandlaw.com"
}