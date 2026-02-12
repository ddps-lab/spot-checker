variable "prefix" {}
variable "lambda_role_arn" {}
variable "log_group_name" {}
variable "log_stream_name" {}

# Azure 인증 정보
variable "azure_subscription_id" {}
variable "azure_tenant_id" {}
variable "azure_client_id" {}
variable "azure_client_secret" {}

# Azure 리소스 설정
variable "azure_region" {
  type        = string
  description = "Azure region for this deployment (display name, e.g. 'US West 3')"
}

# Lambda Layer
variable "azure_sdk_layer_arn" {
  type        = string
  description = "ARN of the Azure SDK Lambda Layer"
}