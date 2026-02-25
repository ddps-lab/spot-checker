# Dispatcher Lambda (Go, provided.al2023)
resource "aws_lambda_function" "dispatcher" {
  function_name = "${var.prefix}-spot-dispatcher"
  role          = var.lambda_role_arn
  handler       = "bootstrap"
  runtime       = "provided.al2023"
  architectures = ["x86_64"]
  memory_size   = 3008
  timeout       = 60

  filename         = "${path.module}/dispatcher.zip"
  source_code_hash = filebase64sha256("${path.module}/dispatcher.zip")

  environment {
    variables = {
      WORKER_FUNCTION_NAME = var.worker_function_name
    }
  }
}

# CloudWatch Log Group for Dispatcher
resource "aws_cloudwatch_log_group" "dispatcher_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.dispatcher.function_name}"
  retention_in_days = 30
}

# EventBridge Rule - Single rule to trigger Dispatcher
resource "aws_cloudwatch_event_rule" "dispatcher_rule" {
  name                = "${var.prefix}-spot-dispatcher-rule"
  schedule_expression = var.lambda_rate
}

# EventBridge Target
resource "aws_cloudwatch_event_target" "dispatcher_target" {
  rule      = aws_cloudwatch_event_rule.dispatcher_rule.name
  target_id = "${var.prefix}-spot-dispatcher-target"
  arn       = aws_lambda_function.dispatcher.arn
}

# Permission for EventBridge to invoke Dispatcher Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dispatcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.dispatcher_rule.arn
}

# Permission for Dispatcher to invoke Worker Lambda
resource "aws_lambda_permission" "allow_dispatcher_invoke_worker" {
  statement_id  = "AllowDispatcherInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.worker_function_name
  principal     = "lambda.amazonaws.com"
  source_arn    = aws_lambda_function.dispatcher.arn
}
