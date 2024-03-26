resource "aws_iam_role" "get-ondemand-status-change-lambda-role" {
  name = "${var.prefix}-get-ondemand-status-change-${var.region}-role"

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

resource "aws_iam_role_policy_attachment" "get-ondemand-status-change-lambda_basic_policy" {
  role       = aws_iam_role.get-ondemand-status-change-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "get-ondemand-status-change-lambda_EC2_policy" {
  role       = aws_iam_role.get-ondemand-status-change-lambda-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}
