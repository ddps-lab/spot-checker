# Monitor VM Status Lambda Module
module "monitor-vm-status" {
  source = "./monitor-vm-status"
  
  prefix             = var.prefix
  lambda_role_arn    = aws_iam_role.monitor_vm_status_lambda_role.arn
  log_group_name     = var.log_group_name
  log_stream_name    = var.log_stream_name
  
  # Azure 인증 정보
  azure_subscription_id = var.azure_subscription_id
  azure_tenant_id       = var.azure_tenant_id
  azure_client_id       = var.azure_client_id
  azure_client_secret   = var.azure_client_secret
  
  # Lambda Layer
  azure_sdk_layer_arn = aws_lambda_layer_version.azure_sdk_layer.arn
}

