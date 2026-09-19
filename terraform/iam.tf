# IAM Role for CloudCostGuard Lambda execution
resource "aws_iam_role" "lambda_role" {
  name = "CloudCostGuard-Lambda-ExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = "CloudCostGuard"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# 1. Pure read-only audit policy (Least Privilege)
resource "aws_iam_policy" "audit_policy" {
  name        = "CloudCostGuard-AuditPolicy"
  description = "Allows CloudCostGuard read-only inspection of resources and CloudWatch metrics"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AuditReadOnlyPermissions"
        Effect = "Allow"
        Action = [
          "ec2:DescribeVolumes",
          "ec2:DescribeAddresses",
          "ec2:DescribeInstances",
          "ec2:DescribeSnapshots",
          "ec2:DescribeImages",
          "cloudwatch:GetMetricData",
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTargetGroups",
          "elasticloadbalancing:DescribeTargetHealth",
          "s3:ListAllMyBuckets",
          "s3:GetBucketLocation",
          "s3:GetLifecycleConfiguration",
          "s3:ListBucketMultipartUploads"
        ]
        Resource = "*"
      }
    ]
  })
}

# 2. Dedicated remediation policy (Only active if remediation is enabled)
resource "aws_iam_policy" "remediation_policy" {
  name        = "CloudCostGuard-RemediationPolicy"
  description = "Allows CloudCostGuard to tag waste resources or stop non-prod EC2 instances"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RemediationTaggingAndStop"
        Effect = "Allow"
        Action = [
          "ec2:CreateTags",
          "ec2:StopInstances"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach basic CloudWatch logging execution policy
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach auditing policy (Always active)
resource "aws_iam_role_policy_attachment" "lambda_audit" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.audit_policy.arn
}

# Attach remediation policy ONLY when active enforcement is requested
resource "aws_iam_role_policy_attachment" "lambda_remediation" {
  count      = var.apply_tags || (var.stop_idle_ec2 && var.safety_opt_in) ? 1 : 0
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.remediation_policy.arn
}
