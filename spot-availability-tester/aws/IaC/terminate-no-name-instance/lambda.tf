resource "aws_lambda_function" "lambda" {
  function_name = "${var.prefix}-terminate-no-name-instances"
  architectures = ["x86_64"]
  memory_size   = 128
  timeout       = 30
  runtime       = "python3.11"
  handler       = "terminate-no-name-instances.lambda_handler"
  filename      = "terminate-no-name-instances.zip"
  role          = var.lambda_role_arn
}

resource "aws_cloudwatch_log_group" "lambda-cloudwatch-log-group" {
  name = "/aws/lambda/${aws_lambda_function.lambda.function_name}"
  retention_in_days = 30
}

# EventBridge Rule
resource "aws_cloudwatch_event_rule" "eventbridge-rule" {
  name                = "one-minute-terminate-no-name-instances"
  schedule_expression = "rate(1 minute)"
}

# Target for EventBridge to trigger Lambda
resource "aws_cloudwatch_event_target" "eventbridge-target" {
  rule      = aws_cloudwatch_event_rule.eventbridge-rule.name
  target_id = "one-minute-terminate-no-name-instances"
  arn       = aws_lambda_function.lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_rw_fallout_retry_step_deletion_lambda" {
  statement_id = "AllowExecutionFromCloudWatch"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.eventbridge-rule.arn
}
