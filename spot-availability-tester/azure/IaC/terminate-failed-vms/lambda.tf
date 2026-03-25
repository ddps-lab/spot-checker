resource "aws_cloudwatch_log_group" "lambda-cloudwatch-log-group" {
  name = "/aws/lambda/${aws_lambda_function.lambda.function_name}"
  retention_in_days = 30
}

resource "aws_lambda_function" "lambda" {
  function_name = "${var.prefix}-terminate-failed-vms"
  architectures = ["x86_64"]
  memory_size   = 256  # Azure SDK 사용으로 메모리 증가
  timeout       = 60   # Azure API 호출 시간 고려
  runtime       = "python3.11"
  handler       = "terminate-pending-instances.lambda_handler"
  filename      = "terminate-pending-instances.zip"
  role          = var.lambda_role_arn
  layers        = [var.azure_sdk_layer_arn]

  environment {
    variables = {
      LOG_GROUP_NAME         = var.log_group_name
      LOG_STREAM_NAME        = var.log_stream_name
      PREFIX                 = var.prefix
      AZURE_SUBSCRIPTION_ID  = var.azure_subscription_id
      AZURE_TENANT_ID        = var.azure_tenant_id
      AZURE_CLIENT_ID        = var.azure_client_id
      AZURE_CLIENT_SECRET    = var.azure_client_secret
      AZURE_REGION           = var.azure_region
    }
  }
}

# EventBridge Rule - 1분마다 spot-test- VM 정리
resource "aws_cloudwatch_event_rule" "eventbridge-rule" {
  name                = "${var.prefix}-terminate-failed-vms"
  description         = "Delete all spot-test-* VMs every 1 minute"
  schedule_expression = "rate(1 minute)"
  state               = "DISABLED"  # 동기 삭제 전환으로 비활성화 (2026-03-02)
}

# Target for EventBridge to trigger Lambda
resource "aws_cloudwatch_event_target" "eventbridge-target" {
  rule      = aws_cloudwatch_event_rule.eventbridge-rule.name
  target_id = "${var.prefix}-terminate-pending-instances"
  arn       = aws_lambda_function.lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_rw_fallout_retry_step_deletion_lambda" {
  statement_id = "AllowExecutionFromCloudWatch"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.eventbridge-rule.arn
}
