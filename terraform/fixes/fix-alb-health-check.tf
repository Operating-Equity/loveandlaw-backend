# Fix for ALB health check configuration
# This file contains the corrected health check settings

# Update the ALB target group health check
resource "aws_lb_target_group" "main_fixed" {
  name        = "loveandlaw-production-tg-fixed"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.existing.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 10  # Increased from 5 to 10
    unhealthy_threshold = 3   # Increased from 2 to 3
  }

  deregistration_delay = 30

  tags = {
    Name        = "loveandlaw-production-tg-fixed"
    Environment = "production"
  }
}

# Data source to get existing VPC
data "aws_vpc" "existing" {
  filter {
    name   = "tag:Name"
    values = ["loveandlaw-production-vpc"]
  }
}