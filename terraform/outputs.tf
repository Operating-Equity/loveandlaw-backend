# Terraform Outputs

output "api_gateway_rest_endpoint" {
  description = "REST API endpoint"
  value       = module.api_gateway.rest_api_endpoint
}

output "api_gateway_websocket_endpoint" {
  description = "WebSocket API endpoint"
  value       = module.api_gateway.websocket_api_endpoint
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = module.ecs.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "monitoring_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.monitoring.dashboard_url
}

output "sns_alerts_topic" {
  description = "SNS topic ARN for alerts"
  value       = module.monitoring.alerts_topic_arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = join(",", module.networking.private_subnets)
}

output "dynamodb_conversations_table" {
  description = "DynamoDB conversations table name"
  value       = module.database.conversations_table_name
}

output "dynamodb_profiles_table" {
  description = "DynamoDB user profiles table name"
  value       = module.database.profiles_table_name
}