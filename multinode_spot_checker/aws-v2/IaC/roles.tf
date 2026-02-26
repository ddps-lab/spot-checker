# ============================================================
# Lambda IAM Roles for aws-v2 modules
# ============================================================

# Get current AWS account ID for proper IAM resource scoping
data "aws_caller_identity" "current" {}


# ── get-spot-status-change Role ─────────────────────────────

resource "aws_iam_role" "get-spot-status-change-role" {
  name = "${var.prefix}-lambda-get-spot-status-change-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "get-spot-status-change-policy" {
  name = "${var.prefix}-lambda-get-spot-status-change-policy"
  role = aws_iam_role.get-spot-status-change-role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:${var.log_group_name}:*"
      }
    ]
  })
}

# ── restart-closed-request Role ────────────────────────────

resource "aws_iam_role" "restart-closed-request-role" {
  name = "${var.prefix}-lambda-restart-closed-request-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "restart-closed-request-policy" {
  name = "${var.prefix}-lambda-restart-closed-request-policy"
  role = aws_iam_role.restart-closed-request-role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeSpotInstanceRequests",
          "ec2:RequestSpotInstances"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:${var.log_group_name}:*"
      },
      {
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = var.iam_instance_profile_arn
      }
    ]
  })
}

# ── get-spot-rebalance Role ────────────────────────────────

resource "aws_iam_role" "get-spot-rebalance-role" {
  name = "${var.prefix}-lambda-get-spot-rebalance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "get-spot-rebalance-policy" {
  name = "${var.prefix}-lambda-get-spot-rebalance-policy"
  role = aws_iam_role.get-spot-rebalance-role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:${var.log_group_name}:*"
      }
    ]
  })
}

# ── get-spot-interruption Role ─────────────────────────────

resource "aws_iam_role" "get-spot-interruption-role" {
  name = "${var.prefix}-lambda-get-spot-interruption-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "get-spot-interruption-policy" {
  name = "${var.prefix}-lambda-get-spot-interruption-policy"
  role = aws_iam_role.get-spot-interruption-role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:${var.log_group_name}:*"
      }
    ]
  })
}

# ── log-instance-count Role ────────────────────────────────

resource "aws_iam_role" "log-instance-count-role" {
  name = "${var.prefix}-lambda-log-instance-count-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "log-instance-count-policy" {
  name = "${var.prefix}-lambda-log-instance-count-policy"
  role = aws_iam_role.log-instance-count-role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeSpotInstanceRequests"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:${var.log_group_name}:*"
      }
    ]
  })
}
