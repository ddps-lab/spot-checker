# Lambda 실행 역할
resource "aws_iam_role" "monitor_vm_status_lambda_role" {
  name = "${var.prefix}-monitor-vm-status-lambda-role"

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
}

# CloudWatch Logs 권한
resource "aws_iam_role_policy" "monitor_vm_status_lambda_logs_policy" {
  name = "${var.prefix}-monitor-vm-status-lambda-logs-policy"
  role = aws_iam_role.monitor_vm_status_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Lambda 기본 실행 정책 연결
resource "aws_iam_role_policy_attachment" "monitor_vm_status_lambda_basic_execution" {
  role       = aws_iam_role.monitor_vm_status_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

