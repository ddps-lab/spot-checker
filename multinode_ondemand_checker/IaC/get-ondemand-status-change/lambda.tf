resource "aws_cloudwatch_log_group" "lambda-cloudwatch-log-group" {
  name              = "/aws/lambda/${aws_lambda_function.lambda.function_name}"
  retention_in_days = 30
}


resource "aws_lambda_function" "lambda" {
  function_name = "${var.prefix}-get-ondemand-status-change"
  architectures = ["x86_64"]
  memory_size   = 128
  timeout       = 30
  runtime       = "python3.11"
  handler       = "get-ondemand-status-change.lambda_handler"
  filename      = "get-ondemand-status-change.zip"
  role          = var.lambda_role_arn

  environment {
    variables = {
      LOG_GROUP_NAME  = var.log_group_name,
      LOG_STREAM_NAME = var.log_stream_name_chage_status,
    }
  }
}

# EventBridge Rule
resource "aws_cloudwatch_event_rule" "eventbridge-rule" {
  name = "${var.prefix}-get-ondemand-status-change"
  event_pattern = jsonencode({
    source      = ["aws.ec2"],
    detail-type = ["EC2 Instance State-change Notification"],
    detail = {
      state = ["pending", "running", "shutting-down", "terminated"]
    }
  })
}

# Target for EventBridge to trigger Lambda
resource "aws_cloudwatch_event_target" "eventbridge-target" {
  rule      = aws_cloudwatch_event_rule.eventbridge-rule.name
  target_id = "${var.prefix}-get-ondemand-status-change"
  arn       = aws_lambda_function.lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_rw_fallout_retry_step_deletion_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.eventbridge-rule.arn
}
