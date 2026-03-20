resource "aws_cloudwatch_log_group" "lambda-cloudwatch-log-group" {
  name = "/aws/lambda/${aws_lambda_function.lambda.function_name}"
  retention_in_days = 30

  depends_on = [ aws_lambda_function.lambda ]
}


resource "aws_lambda_function" "lambda" {
  function_name = "${var.prefix}-get-spot-rebalance"
  architectures = ["x86_64"]
  memory_size   = 128
  timeout       = 30
  runtime       = "python3.11"
  handler       = "get-spot-rebalance.lambda_handler"
  filename      = "get-spot-rebalance.zip"
  source_code_hash = filebase64sha256("get-spot-rebalance.zip")
  role          = var.lambda_role_arn

  environment {
    variables = {
      LOG_GROUP_NAME    = var.log_group_name,
      LOG_STREAM_NAME   = var.log_stream_name_rebalance,
    }
  }
}

# EventBridge Rule
resource "aws_cloudwatch_event_rule" "eventbridge-rule" {
  name                = "${var.prefix}-get-spot-rebalance"
  event_pattern = jsonencode({
    source = ["aws.ec2"],
    detail-type = ["EC2 Instance Rebalance Recommendation"],
  })
}

# Target for EventBridge to trigger Lambda
resource "aws_cloudwatch_event_target" "eventbridge-target" {
  rule      = aws_cloudwatch_event_rule.eventbridge-rule.name
  target_id = "${var.prefix}-get-spot-rebalance"
  arn       = aws_lambda_function.lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  statement_id = "AllowExecutionFromCloudWatch"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.eventbridge-rule.arn
}
