output "lambda_function_name" {
  description = "Name of the deployed CloudCostGuard Lambda function"
  value       = aws_lambda_function.cloudcostguard.function_name
}

output "lambda_function_arn" {
  description = "ARN of the deployed CloudCostGuard Lambda function"
  value       = aws_lambda_function.cloudcostguard.arn
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge scheduled cron rule"
  value       = aws_cloudwatch_event_rule.weekly_audit.arn
}

output "iam_role_arn" {
  description = "ARN of the IAM Role utilized by CloudCostGuard"
  value       = aws_iam_role.lambda_role.arn
}
