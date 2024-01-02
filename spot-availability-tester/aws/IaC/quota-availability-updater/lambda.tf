resource "aws_cloudwatch_log_group" "lambda-cloudwatch-log-group" {
  name              = "/aws/lambda/${aws_lambda_function.lambda.function_name}"
  retention_in_days = 30
}
resource "aws_lambda_function" "lambda" {
  function_name = "${var.prefix}-quota-availability-updater"
  architectures = ["x86_64"]
  memory_size   = 128
  timeout       = 30
  runtime       = "python3.11"
  handler       = "quota-availability-updater.lambda_handler"
  filename      = "quota-availability-updater.zip"
  role          = var.lambda_role_arn


  environment {
    variables = {
        REGION = var.region
        DDBNAME = "${var.prefix}-DDDCHECKTABLE"
    }
  }
}

resource "aws_cloudwatch_event_rule" "every-30-seconds" {
  name        = "every-30-seconds"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "invoke-lambda-every-30-seconds" {
  rule = aws_cloudwatch_event_rule.every-30-seconds.name
  target_id = "InvokeLambda"
  arn = aws_lambda_function.lambda.arn
}

resource "aws_lambda_permission" "allow-cloudwatch-to-call-quota-checker" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every-30-seconds.arn
}
