variable "region" {
  description = "AWS region for Lambda deployment"
  type        = string
}

variable "prefix" {
  description = "Prefix for resource naming"
  type        = string
}

variable "awscli_profile" {
  description = "AWS CLI profile name"
  type        = string
  default     = "default"
}

variable "log_group_name" {
  description = "CloudWatch Log Group name"
  type        = string
}

variable "log_stream_name" {
  description = "CloudWatch Log Stream name"
  type        = string
}

# Azure 인증 정보
variable "azure_subscription_id" {
  description = "Azure Subscription ID"
  type        = string
}

variable "azure_tenant_id" {
  description = "Azure Tenant ID"
  type        = string
}

variable "azure_client_id" {
  description = "Azure Client ID (Service Principal)"
  type        = string
}

variable "azure_client_secret" {
  description = "Azure Client Secret"
  type        = string
  sensitive   = true
}

