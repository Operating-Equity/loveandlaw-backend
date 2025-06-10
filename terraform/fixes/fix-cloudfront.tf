# Fix CloudFront configuration to use dynamic API Gateway endpoints

# Data sources
data "aws_api_gateway_rest_api" "main" {
  name = "loveandlaw-production-api"
}

data "aws_api_gateway_stage" "main" {
  rest_api_id = data.aws_api_gateway_rest_api.main.id
  stage_name  = "production"
}

data "aws_apigatewayv2_api" "websocket" {
  name = "loveandlaw-production-websocket"
}

data "aws_cloudfront_distribution" "existing" {
  id = var.cloudfront_distribution_id  # You'll need to provide this
}

# Update CloudFront with correct origins
resource "aws_cloudfront_distribution" "fixed" {
  enabled = true
  comment = "loveandlaw production distribution - fixed"
  
  # REST API origin
  origin {
    domain_name = replace(data.aws_api_gateway_stage.main.invoke_url, "https://", "")
    origin_id   = "rest-api"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }
  
  # WebSocket API origin
  origin {
    domain_name = "${data.aws_apigatewayv2_api.websocket.api_id}.execute-api.${var.aws_region}.amazonaws.com"
    origin_id   = "websocket-api"
    origin_path = "/production"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }
  
  # Default behavior for REST API
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "rest-api"
    
    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type", "Accept", "Origin", "Referer"]
      
      cookies {
        forward = "all"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }
  
  # WebSocket behavior
  ordered_cache_behavior {
    path_pattern     = "/ws*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "websocket-api"
    
    forwarded_values {
      query_string = true
      headers      = ["*"]
      
      cookies {
        forward = "all"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }
  
  # API routes
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "rest-api"
    
    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type", "Accept", "Origin", "Referer"]
      
      cookies {
        forward = "all"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }
  
  # Health check endpoint
  ordered_cache_behavior {
    path_pattern     = "/health"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "rest-api"
    
    forwarded_values {
      query_string = false
      headers      = []
      
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    cloudfront_default_certificate = true
  }
  
  tags = {
    Name        = "loveandlaw-production-cloudfront-fixed"
    Environment = "production"
  }
}

variable "cloudfront_distribution_id" {
  description = "Existing CloudFront distribution ID"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}