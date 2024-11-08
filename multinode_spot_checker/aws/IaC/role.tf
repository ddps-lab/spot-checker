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