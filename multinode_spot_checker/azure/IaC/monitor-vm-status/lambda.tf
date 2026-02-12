# Lambda 함수
resource "aws_lambda_function" "monitor_vm_status" {
  filename         = data.archive_file.monitor_vm_status_lambda.output_path
  function_name    = "${var.prefix}-monitor-vm-status"
  role            = var.lambda_role_arn
  handler         = "monitor-vm-status.lambda_handler"
  source_code_hash = data.archive_file.monitor_vm_status_lambda.output_base64sha256
  runtime         = "python3.11"
  timeout         = 300  # 5분
  memory_size     = 512  # 512MB

  layers = [var.azure_sdk_layer_arn]

  environment {
    variables = {
      LOG_GROUP_NAME        = var.log_group_name
      LOG_STREAM_NAME       = var.log_stream_name
      PREFIX                = var.prefix
      AZURE_SUBSCRIPTION_ID = var.azure_subscription_id
      AZURE_TENANT_ID       = var.azure_tenant_id
      AZURE_CLIENT_ID       = var.azure_client_id
      AZURE_CLIENT_SECRET   = var.azure_client_secret
    }
  }
}

# EventBridge 스케줄 (1분마다 실행)
resource "aws_cloudwatch_event_rule" "monitor_vm_status_schedule" {
  name                = "${var.prefix}-monitor-vm-status-schedule"
  description         = "Trigger monitor-vm-status Lambda every 1 minute"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "monitor_vm_status_target" {
  rule      = aws_cloudwatch_event_rule.monitor_vm_status_schedule.name
  target_id = "monitor-vm-status-lambda"
  arn       = aws_lambda_function.monitor_vm_status.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.monitor_vm_status.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.monitor_vm_status_schedule.arn
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "monitor_vm_status_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.monitor_vm_status.function_name}"
  retention_in_days = 7
}

