variable "prefix" {
  description = "Prefix for resource naming"
  type        = string
}

variable "lambda_role_arn" {
  description = "Lambda execution role ARN"
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch Log Group name"
  type        = string
}

variable "log_stream_name" {
  description = "CloudWatch Log Stream name"
  type        = string
}

variable "azure_subscription_id" {
  description = "Azure Subscription ID"
  type        = string
}

variable "azure_tenant_id" {
  description = "Azure Tenant ID"
  type        = string
}

variable "azure_client_id" {
  description = "Azure Client ID"
  type        = string
}

variable "azure_client_secret" {
  description = "Azure Client Secret"
  type        = string
  sensitive   = true
}

variable "azure_sdk_layer_arn" {
  description = "Azure SDK Lambda Layer ARN"
  type        = string
}

