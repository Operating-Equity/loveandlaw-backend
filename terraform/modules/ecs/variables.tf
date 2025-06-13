variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnets" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "public_subnets" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "container_image" {
  description = "Container image URI"
  type        = string
  default     = "latest"
}

variable "container_image_tag" {
  description = "Container image tag"
  type        = string
  default     = "latest"
}

variable "container_cpu" {
  description = "Container CPU units"
  type        = number
}

variable "container_memory" {
  description = "Container memory in MB"
  type        = number
}

variable "secrets_arn" {
  description = "ARN of the secrets in Secrets Manager"
  type        = string
}

variable "dynamodb_tables" {
  description = "DynamoDB table names"
  type = object({
    conversations = string
    profiles      = string
  })
}

variable "redis_endpoint" {
  description = "Redis endpoint"
  type        = string
}

variable "redis_auth_secret_arn" {
  description = "ARN of Redis auth token secret"
  type        = string
}

variable "elasticsearch_endpoint" {
  description = "Elasticsearch endpoint"
  type        = string
}

variable "clerk_publishable_key" {
  description = "Clerk publishable key"
  type        = string
}

variable "clerk_frontend_api" {
  description = "Clerk frontend API domain"
  type        = string
}