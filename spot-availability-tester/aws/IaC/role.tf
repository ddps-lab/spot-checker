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

resource "aws_iam_role" "terminate-no-name-instance-lambda-role" {
  name = "${var.prefix}-terminate-no-name-instances-${var.region}-role"

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

resource "aws_iam_role_policy_attachment" "terminate-no-name-instance-lambda_basic_policy" {
  role       = aws_iam_role.terminate-no-name-instance-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "terminate-no-name-instance-lambda_EC2_policy" {
  role       = aws_iam_role.terminate-no-name-instance-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

resource "aws_iam_role" "terminate-pending-instance-lambda-role" {
  name = "${var.prefix}-terminate-pending-instances-${var.region}-role"

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
  role       = aws_iam_role.terminate-pending-instance-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "terminate-pending-instance-lambda_EC2_policy" {
  role       = aws_iam_role.terminate-pending-instance-lambda-role.name
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
