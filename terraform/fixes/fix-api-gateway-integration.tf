# Fix for API Gateway integration
# This ensures proper routing from API Gateway to ALB

# Data sources to get existing resources
data "aws_api_gateway_rest_api" "existing" {
  name = "loveandlaw-production-api"
}

data "aws_lb" "existing_alb" {
  name = "loveandlaw-production-alb"
}

data "aws_api_gateway_vpc_link" "existing" {
  name = "loveandlaw-production-vpc-link"
}

# Fix the health endpoint integration
resource "aws_api_gateway_resource" "health" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  parent_id   = data.aws_api_gateway_rest_api.existing.root_resource_id
  path_part   = "health"
}

resource "aws_api_gateway_method" "health" {
  rest_api_id   = data.aws_api_gateway_rest_api.existing.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "health" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health.http_method

  type                    = "HTTP_PROXY"
  integration_http_method = "GET"
  uri                     = "http://${data.aws_lb.existing_alb.dns_name}/health"
  connection_type         = "VPC_LINK"
  connection_id           = data.aws_api_gateway_vpc_link.existing.id

  request_templates = {
    "application/json" = ""
  }
}

resource "aws_api_gateway_method_response" "health" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "health" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health.http_method
  status_code = aws_api_gateway_method_response.health.status_code

  response_templates = {
    "application/json" = ""
  }
}

# Deploy the changes
resource "aws_api_gateway_deployment" "fix" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  stage_name  = "production"

  depends_on = [
    aws_api_gateway_method.health,
    aws_api_gateway_integration.health
  ]

  lifecycle {
    create_before_destroy = true
  }
}