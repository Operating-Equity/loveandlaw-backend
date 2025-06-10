variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "alb_endpoint" {
  description = "ALB endpoint DNS name"
  type        = string
}

variable "vpc_link_id" {
  description = "VPC Link ID for API Gateway"
  type        = string
}