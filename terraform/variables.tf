variable "aws_region" {
  description = "AWS region for deploying CloudCostGuard infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "production"
}

variable "scan_regions" {
  description = "Comma-separated AWS regions to audit"
  type        = string
  default     = "us-east-1,us-west-2,ap-south-1,eu-west-1"
}

variable "schedule_expression" {
  description = "Cron or rate expression for EventBridge trigger (Default: Every Monday at 8:00 AM UTC)"
  type        = string
  default     = "cron(0 8 ? * MON *)"
}

variable "dry_run" {
  description = "Whether to run in audit-only dry-run mode"
  type        = bool
  default     = true
}

variable "apply_tags" {
  description = "Whether to automatically apply cleanup tags to identified waste resources"
  type        = bool
  default     = false
}

variable "stop_idle_ec2" {
  description = "Whether to automatically stop underutilized development EC2 compute instances"
  type        = bool
  default     = false
}

variable "safety_opt_in" {
  description = "Explicit safety opt-in required before enabling automated EC2 instance stopping"
  type        = bool
  default     = false
}

variable "slack_webhook_url" {
  description = "Slack Incoming Webhook URL for audit notifications (leave empty if not using Slack)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "lambda_timeout_seconds" {
  description = "Lambda execution timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory_mb" {
  description = "Memory allocated to Lambda function in MB"
  type        = number
  default     = 256
}
