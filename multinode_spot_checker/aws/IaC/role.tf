resource "aws_iam_role" "get-spot-status-change-lambda-role" {
  name = "${var.prefix}-get-spot-status-change-${var.region}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "get-spot-status-change-lambda_basic_policy" {
  role       = aws_iam_role.get-spot-status-change-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "get-spot-status-change-lambda_EC2_policy" {
  role       = aws_iam_role.get-spot-status-change-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

resource "aws_iam_role" "restart-closed-request-lambda-role" {
  name = "${var.prefix}-restart-closed-request-${var.region}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "restart-closed-request-lambda_basic_policy" {
  role       = aws_iam_role.restart-closed-request-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "restart-closed-request-lambda_EC2_policy" {
  role       = aws_iam_role.restart-closed-request-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

resource "aws_iam_role_policy" "restart-closed-request-lambda_passrole_policy" {
  name   = "${var.prefix}-lambda-passrole-policy"
  role   = aws_iam_role.restart-closed-request-lambda-role.name

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "iam:PassRole",
        Resource = "arn:aws:iam::741926482963:role/EC2toEC2_CW"  # EC2 인스턴스에 전달할 역할 ARN
      }
    ]
  })
}

# ===== get-spot-rebalance Lambda Role =====
resource "aws_iam_role" "get-spot-rebalance-lambda-role" {
  name = "${var.prefix}-get-spot-rebalance-${var.region}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "get-spot-rebalance-lambda_basic_policy" {
  role       = aws_iam_role.get-spot-rebalance-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "get-spot-rebalance-lambda_EC2_policy" {
  role       = aws_iam_role.get-spot-rebalance-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

# ===== get-spot-interruption Lambda Role =====
resource "aws_iam_role" "get-spot-interruption-lambda-role" {
  name = "${var.prefix}-get-spot-interruption-${var.region}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "get-spot-interruption-lambda_basic_policy" {
  role       = aws_iam_role.get-spot-interruption-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "get-spot-interruption-lambda_EC2_policy" {
  role       = aws_iam_role.get-spot-interruption-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

# ===== log-instance-count Lambda Role =====
resource "aws_iam_role" "log-instance-count-lambda-role" {
  name = "${var.prefix}-log-instance-count-${var.region}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "log-instance-count-lambda_basic_policy" {
  role       = aws_iam_role.log-instance-count-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "log-instance-count-lambda_EC2_policy" {
  role       = aws_iam_role.log-instance-count-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

# ===== FIS (Fault Injection Simulator) Role =====
resource "aws_iam_role" "fis-role" {
  name = "${var.prefix}-fis-role-${var.region}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "fis.amazonaws.com"
      }
    }]
  })
}

# FIS가 EC2 및 Spot 인스턴스를 제어할 수 있도록 권한 부여
resource "aws_iam_role_policy" "fis-ec2-policy" {
  name = "${var.prefix}-fis-ec2-policy"
  role = aws_iam_role.fis-role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateTags",
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus",
          "ec2:RebootInstances",
          "ec2:StopInstances",
          "ec2:StartInstances",
          "ec2:TerminateInstances",
          "ec2:SendCommand",
          "ec2:SendSpotInstanceInterruptions",
          "ec2:ModifySpotFleetRequest",
          "ec2:CancelSpotFleetRequests",
          "ec2:DescribeSpotFleetRequests",
          "ec2:DescribeSpotInstanceRequests"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetAutomationExecution",
          "ssm:StartAutomationExecution",
          "ssm:StopAutomationExecution"
        ]
        Resource = "*"
      }
    ]
  })
}