terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Package Lambda function source code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/build/cloudcostguard.zip"
}

# CloudWatch Log Group for structured audit logs
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/CloudCostGuard-Optimizer"
  retention_in_days = 14

  tags = {
    Project   = "CloudCostGuard"
    ManagedBy = "Terraform"
  }
}

# AWS Lambda Function
resource "aws_lambda_function" "cloudcostguard" {
  function_name = "CloudCostGuard-Optimizer"
  description   = "FinOps Multi-Resource Waste Auditor and Optimizer"
  role          = aws_iam_role.lambda_role.arn
  handler       = "cloudcostguard.lambda_handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.lambda_timeout_seconds
  memory_size   = var.lambda_memory_mb

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      AWS_SCAN_REGIONS  = var.scan_regions
      DRY_RUN           = tostring(var.dry_run)
      APPLY_TAGS        = tostring(var.apply_tags)
      STOP_IDLE_EC2     = tostring(var.stop_idle_ec2)
      SAFETY_OPT_IN     = tostring(var.safety_opt_in)
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy_attachment.lambda_audit
  ]

  tags = {
    Project   = "CloudCostGuard"
    ManagedBy = "Terraform"
  }
}

# EventBridge Rule (Scheduled Cron Trigger)
resource "aws_cloudwatch_event_rule" "weekly_audit" {
  name                = "CloudCostGuard-WeeklySchedule"
  description         = "Triggers CloudCostGuard automated FinOps audit"
  schedule_expression = var.schedule_expression

  tags = {
    Project   = "CloudCostGuard"
    ManagedBy = "Terraform"
  }
}

# EventBridge Target pointing to Lambda
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.weekly_audit.name
  target_id = "CloudCostGuardLambda"
  arn       = aws_lambda_function.cloudcostguard.arn
}

# Lambda Permission for EventBridge invocation
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cloudcostguard.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_audit.arn
}
