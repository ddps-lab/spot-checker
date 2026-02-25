resource "aws_iam_role" "spot-availability-tester-lambda-role" {
  name = "${var.prefix}-spot-availability-tester-${var.region}-role"

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

resource "aws_iam_role_policy_attachment" "spot-availability-tester-lambda_basic_policy" {
  role       = aws_iam_role.spot-availability-tester-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "spot-availability-tester-lambda_EC2_policy" {
  role       = aws_iam_role.spot-availability-tester-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

resource "aws_iam_role_policy_attachment" "spot-availability-tester-lambda_DynamoDB_policy" {
  role       = aws_iam_role.spot-availability-tester-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

# spot-availability-tester Lambda가 terminate-failed-vms Lambda를 invoke할 수 있는 권한
resource "aws_iam_role_policy" "spot-availability-tester-lambda_invoke_terminate" {
  name = "${var.prefix}-spot-availability-tester-invoke-terminate-${var.region}"
  role = aws_iam_role.spot-availability-tester-lambda-role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${var.prefix}-terminate-failed-vms"
      }
    ]
  })
}

# AWS 계정 ID 조회용 data source
data "aws_caller_identity" "current" {}

resource "aws_iam_role" "terminate-orphan-disk-lambda-role" {
  name = "${var.prefix}-terminate-orphan-disk-${var.region}-role"

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

resource "aws_iam_role_policy_attachment" "terminate-orphan-disk-lambda_basic_policy" {
  role       = aws_iam_role.terminate-orphan-disk-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "terminate-orphan-disk-lambda_EC2_policy" {
  role       = aws_iam_role.terminate-orphan-disk-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

resource "aws_iam_role" "terminate-failed-vms-lambda-role" {
  name = "${var.prefix}-terminate-failed-vms-${var.region}-role"

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

resource "aws_iam_role_policy_attachment" "terminate-pending-instance-lambda_basic_policy" {
  role       = aws_iam_role.terminate-failed-vms-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "terminate-pending-instance-lambda_EC2_policy" {
  role       = aws_iam_role.terminate-failed-vms-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

resource "aws_iam_role" "quota-availability-updater-lambda-role" {
  name = "${var.prefix}-lambda_dynamodb_full_access-${var.region}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
      },
    ],
  })
}


resource "aws_iam_role_policy_attachment" "quota-availability-updater-lambda_basic_policy" {
  role       = aws_iam_role.quota-availability-updater-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "quota-availability-updater-dynamodb-attachment" {
  role       = aws_iam_role.quota-availability-updater-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

resource "aws_iam_role_policy_attachment" "quota-availability-updater-ec2-attachment" {
  role       = aws_iam_role.quota-availability-updater-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

resource "aws_iam_role" "tester-ec2-role" {
  name = "${var.prefix}-tester-ec2-${var.region}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        },
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "tester-ec2-role-admin-access" {
  role       = aws_iam_role.tester-ec2-role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_instance_profile" "tester-ec2-role-instance-profile" {
  name = "${var.prefix}-tester-ec2-role-${var.region}-instance-profile"
  role = aws_iam_role.tester-ec2-role.name
}

resource "aws_iam_role" "dispatcher-lambda-role" {
  count = var.use_ec2 ? 0 : 1
  name  = "${var.prefix}-spot-dispatcher-${var.region}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "dispatcher-lambda-basic-policy" {
  count      = var.use_ec2 ? 0 : 1
  role       = aws_iam_role.dispatcher-lambda-role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "dispatcher-lambda-invoke-policy" {
  count = var.use_ec2 ? 0 : 1
  name  = "${var.prefix}-dispatcher-invoke-worker-policy"
  role  = aws_iam_role.dispatcher-lambda-role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = "*"
    }]
  })
}