# Monitoring Module - CloudWatch Dashboards, Alarms, and Notifications

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"

  tags = {
    Name        = "${var.project_name}-${var.environment}-alerts"
    Environment = var.environment
  }
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${var.environment}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # ECS Service Metrics
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${var.project_name}-api", "ClusterName", var.ecs_cluster_name, { stat = "Average" }],
            [".", "MemoryUtilization", ".", ".", ".", ".", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "ECS Service CPU/Memory"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      # API Gateway Metrics
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", "${var.project_name}-${var.environment}-api", { stat = "Sum" }],
            [".", "4XXError", ".", ".", { stat = "Sum", color = "#ff7f0e" }],
            [".", "5XXError", ".", ".", { stat = "Sum", color = "#d62728" }]
          ]
          period = 300
          stat   = "Sum"
          region = data.aws_region.current.name
          title  = "API Gateway Requests"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      # API Gateway Latency
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiName", "${var.project_name}-${var.environment}-api", { stat = "p50" }],
            ["...", { stat = "p90" }],
            ["...", { stat = "p99" }]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "API Gateway Latency (ms)"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      # WebSocket Connections
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "ConnectCount", "ApiName", "${var.project_name}-${var.environment}-websocket", { stat = "Sum" }],
            [".", "MessageCount", ".", ".", { stat = "Sum" }],
            [".", "IntegrationError", ".", ".", { stat = "Sum", color = "#d62728" }]
          ]
          period = 300
          stat   = "Sum"
          region = data.aws_region.current.name
          title  = "WebSocket Activity"
        }
      },
      # ALB Target Health
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", local.target_group_name, "LoadBalancer", local.alb_name, { stat = "Average" }],
            [".", "UnHealthyHostCount", ".", ".", ".", ".", { stat = "Average", color = "#d62728" }]
          ]
          period = 60
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "ALB Target Health"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      # DynamoDB Metrics
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.project_name}-${var.environment}-conversations", { stat = "Sum" }],
            [".", "ConsumedWriteCapacityUnits", ".", ".", { stat = "Sum" }],
            [".", "UserErrors", ".", ".", { stat = "Sum", color = "#d62728" }]
          ]
          period = 300
          stat   = "Sum"
          region = data.aws_region.current.name
          title  = "DynamoDB Usage"
        }
      },
      # ElastiCache Metrics
      {
        type   = "metric"
        x      = 0
        y      = 18
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", "${var.project_name}-${var.environment}-redis-001", { stat = "Average" }],
            [".", "NetworkBytesIn", ".", ".", { stat = "Sum", yAxis = "right" }],
            [".", "NetworkBytesOut", ".", ".", { stat = "Sum", yAxis = "right" }]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "Redis Cache Performance"
        }
      },
      # Custom Application Metrics
      {
        type   = "metric"
        x      = 12
        y      = 18
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["${var.project_name}/${var.environment}", "AllianceBond", { stat = "Average" }],
            [".", "AllianceGoal", { stat = "Average" }],
            [".", "AllianceTask", { stat = "Average" }],
            [".", "EngagementLevel", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "Therapeutic Alliance Metrics"
          yAxis = {
            left = {
              min = 0
              max = 10
            }
          }
        }
      }
    ]
  })
}

# Alarms

# High Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "${var.project_name}-${var.environment}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors API 5XX errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = "${var.project_name}-${var.environment}-api"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-high-error-rate"
    Environment = var.environment
  }
}

# High Latency Alarm
resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "${var.project_name}-${var.environment}-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Average"
  threshold           = "1000"
  alarm_description   = "This metric monitors API latency"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = "${var.project_name}-${var.environment}-api"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-high-latency"
    Environment = var.environment
  }
}

# ECS Service CPU Alarm
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = "${var.project_name}-api"
    ClusterName = var.ecs_cluster_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ecs-cpu-high"
    Environment = var.environment
  }
}

# ECS Service Memory Alarm
resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  alarm_name          = "${var.project_name}-${var.environment}-ecs-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS memory utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = "${var.project_name}-api"
    ClusterName = var.ecs_cluster_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ecs-memory-high"
    Environment = var.environment
  }
}

# ALB Unhealthy Host Alarm
resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_hosts" {
  alarm_name          = "${var.project_name}-${var.environment}-alb-unhealthy-hosts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors ALB unhealthy hosts"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TargetGroup  = local.target_group_name
    LoadBalancer = local.alb_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-alb-unhealthy-hosts"
    Environment = var.environment
  }
}

# DynamoDB Throttles Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  alarm_name          = "${var.project_name}-${var.environment}-dynamodb-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "SystemErrors"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors DynamoDB throttles"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TableName = "${var.project_name}-${var.environment}-conversations"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-dynamodb-throttles"
    Environment = var.environment
  }
}

# Redis CPU Alarm
resource "aws_cloudwatch_metric_alarm" "redis_cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors Redis CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = "${var.project_name}-${var.environment}-redis-001"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-redis-cpu-high"
    Environment = var.environment
  }
}

# WebSocket Connection Errors
resource "aws_cloudwatch_metric_alarm" "websocket_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-websocket-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "IntegrationError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "20"
  alarm_description   = "This metric monitors WebSocket integration errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = "${var.project_name}-${var.environment}-websocket"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-websocket-errors"
    Environment = var.environment
  }
}

# Custom Application Metric - High Distress
resource "aws_cloudwatch_metric_alarm" "high_distress" {
  alarm_name          = "${var.project_name}-${var.environment}-high-distress"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "DistressScore"
  namespace           = "${var.project_name}/${var.environment}"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "8"
  alarm_description   = "High distress score detected - requires immediate attention"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  tags = {
    Name        = "${var.project_name}-${var.environment}-high-distress"
    Environment = var.environment
    Severity    = "CRITICAL"
  }
}

# CloudWatch Logs Insights Queries
resource "aws_cloudwatch_query_definition" "error_analysis" {
  name = "${var.project_name}-${var.environment}-error-analysis"

  log_group_names = [
    "/ecs/${var.project_name}-${var.environment}",
    "/aws/apigateway/${var.project_name}-${var.environment}-rest"
  ]

  query_string = <<-EOT
    fields @timestamp, @message
    | filter @message like /ERROR/
    | stats count() by bin(5m)
  EOT
}

resource "aws_cloudwatch_query_definition" "user_sessions" {
  name = "${var.project_name}-${var.environment}-user-sessions"

  log_group_names = [
    "/ecs/${var.project_name}-${var.environment}"
  ]

  query_string = <<-EOT
    fields @timestamp, user_id, session_duration, alliance_bond, alliance_goal, alliance_task
    | filter @message like /session_end/
    | stats avg(session_duration), avg(alliance_bond), avg(alliance_goal), avg(alliance_task) by bin(1h)
  EOT
}

# X-Ray Service Map
resource "aws_xray_sampling_rule" "main" {
  rule_name      = "${var.project_name}-${var.environment}-sampling"
  priority       = 1000
  version        = 1
  reservoir_size = 1
  fixed_rate     = 0.1
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "*"
  resource_arn   = "*"

  attributes = {
    Environment = var.environment
  }
}

# CloudWatch Synthetics Canary for Health Checks
resource "aws_synthetics_canary" "health_check" {
  name                 = "${var.project_name}-${var.environment}-health"
  artifact_s3_location = "s3://${aws_s3_bucket.synthetics.bucket}/canary-artifacts/"
  execution_role_arn   = aws_iam_role.synthetics.arn
  handler              = "apiCanaryBlueprint.handler"
  zip_file             = data.archive_file.synthetics_script.output_path
  runtime_version      = "syn-nodejs-puppeteer-7.0"
  start_canary         = true

  schedule {
    expression = "rate(5 minutes)"
  }

  run_config {
    timeout_in_seconds = 60
    memory_in_mb       = 960
  }

  success_retention_period = 31
  failure_retention_period = 31

  tags = {
    Name        = "${var.project_name}-${var.environment}-health-check"
    Environment = var.environment
  }
}

# S3 Bucket for Synthetics
resource "aws_s3_bucket" "synthetics" {
  bucket = "${var.project_name}-${var.environment}-synthetics"

  tags = {
    Name        = "${var.project_name}-${var.environment}-synthetics"
    Environment = var.environment
  }
}

# IAM Role for Synthetics
resource "aws_iam_role" "synthetics" {
  name = "${var.project_name}-${var.environment}-synthetics"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-synthetics"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "synthetics" {
  role       = aws_iam_role.synthetics.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchSyntheticsFullAccess"
}

# Data sources and locals
data "aws_region" "current" {}

locals {
  alb_arn_parts = split("/", var.alb_arn)
  alb_name      = join("/", slice(local.alb_arn_parts, 1, length(local.alb_arn_parts)))
  # Target group name will be set by ECS module outputs
  target_group_name = "${var.project_name}-${var.environment}-tg"
}

# Archive for Synthetics script
data "archive_file" "synthetics_script" {
  type        = "zip"
  output_path = "/tmp/synthetics.zip"
  
  source {
    content  = <<-EOT
      const synthetics = require('Synthetics');
      const log = require('SyntheticsLogger');

      const apiCanaryBlueprint = async function () {
        const apiEndpoint = "${var.api_endpoint}";
        
        let requestOptions = {
          hostname: apiEndpoint,
          method: 'GET',
          path: '/health',
          port: 443,
          protocol: 'https:',
          timeout: 30000
        };
        
        let response = await synthetics.makeHttpRequest(requestOptions);
        return response;
      };

      exports.handler = async () => {
        return await synthetics.runCanary(apiCanaryBlueprint);
      };
    EOT
    filename = "nodejs/node_modules/apiCanaryBlueprint.js"
  }
}

# Outputs
output "dashboard_url" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}