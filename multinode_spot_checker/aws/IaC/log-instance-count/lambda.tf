resource "aws_cloudwatch_log_group" "lambda-cloudwatch-log-group" {
  name = "/aws/lambda/${aws_lambda_function.lambda.function_name}"
  retention_in_days = 30

  depends_on = [ aws_lambda_function.lambda ]
}


resource "aws_lambda_function" "lambda" {
  function_name = "${var.prefix}-log-instance-count"
  architectures = ["x86_64"]
  memory_size   = 256
  timeout       = 60
  runtime       = "python3.11"
  handler       = "log-instance-count.lambda_handler"
  filename      = "log-instance-count.zip"
  role          = var.lambda_role_arn

  environment {
    variables = {
      LOG_GROUP_NAME                    = var.log_group_name,
      LOG_STREAM_NAME_COUNT             = var.log_stream_name_count,
      LOG_STREAM_NAME_PLACEMENT_FAILED  = var.log_stream_name_placement_failed,
      RECENT_WINDOW_MINUTES             = var.recent_window_minutes,
    }
  }
}

# EventBridge Rule - Schedule based (every N minutes)
resource "aws_cloudwatch_event_rule" "eventbridge-rule" {
  name                = "${var.prefix}-log-instance-count"
  schedule_expression = "rate(${var.count_interval_minutes} minutes)"
}

# Target for EventBridge to trigger Lambda
resource "aws_cloudwatch_event_target" "eventbridge-target" {
  rule      = aws_cloudwatch_event_rule.eventbridge-rule.name
  target_id = "${var.prefix}-log-instance-count"
  arn       = aws_lambda_function.lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  statement_id = "AllowExecutionFromCloudWatch"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.eventbridge-rule.arn
}
