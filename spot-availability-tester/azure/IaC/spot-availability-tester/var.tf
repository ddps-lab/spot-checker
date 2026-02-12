variable "prefix" {}
variable "lambda_role_arn" {}
variable "vpc_id" {}
variable "subnet_ids" {}
variable "subnet_az_names" {}
variable "security_group_id" {}
variable "log_group_name" {}
variable "log_stream_name" {}
variable "instance_types" {}
variable "instance_types_az" {}
variable "lambda_rate" {}
variable "use_ec2" {}
variable "describe_rate" {}

# Azure 인증 정보
variable "azure_subscription_id" {
  type      = string
  sensitive = true
}

variable "azure_tenant_id" {
  type      = string
  sensitive = true
}

variable "azure_client_id" {
  type      = string
  sensitive = true
}

variable "azure_client_secret" {
  type      = string
  sensitive = true
}

variable "azure_nic_pool_size_runtime" {
  type        = number
  default     = 50
  description = "Actual NIC pool size (Lambda 환경변수용)"
}

variable "azure_sdk_layer_arn" {
  type        = string
  description = "ARN of the Azure SDK Lambda Layer"
}