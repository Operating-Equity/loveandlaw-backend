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

variable "conversations_table_name" {
  description = "Name of the DynamoDB conversations table"
  type        = string
  default     = "loveandlaw-conversations"
}

variable "profiles_table_name" {
  description = "Name of the DynamoDB user profiles table"
  type        = string
  default     = "loveandlaw-userprofiles"
}