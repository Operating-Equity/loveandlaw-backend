# DynamoDB Tables for Love & Law

resource "aws_dynamodb_table" "conversations" {
  name           = var.conversations_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  range_key      = "turn_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "turn_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-conversations"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "user_profiles" {
  name           = var.profiles_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-profiles"
    Environment = var.environment
  }
}

# Outputs
output "conversations_table_name" {
  value = aws_dynamodb_table.conversations.name
}

output "conversations_table_arn" {
  value = aws_dynamodb_table.conversations.arn
}

output "profiles_table_name" {
  value = aws_dynamodb_table.user_profiles.name
}

output "profiles_table_arn" {
  value = aws_dynamodb_table.user_profiles.arn
}