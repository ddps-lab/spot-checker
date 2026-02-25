# AWS 관련 변수
variable "awscli_profile" {
  type    = string
  default = ""
}

variable "region" {
  type    = string
  default = ""
}

variable "prefix" {
  type = string
  default = ""
}

# CloudWatch Logs (AWS)
variable "log_group_name" {
  type = string
  default = ""
}

variable "spot_log_stream_name" {
  type = string
  default = ""
}

variable "terminate_log_stream_name" {
  type = string
  default = ""
}

variable "pending_log_stream_name" {
  type = string
  default = ""
}

# AWS EC2 테스트 관련
variable "instance_types" {
  type = list(string)
  default = []
}

variable "instance_types_az" {
  type = list(string)
  default = []
}

variable "lambda_rate" {
  type = string
  default = ""
}

variable "describe_rate" {
  type = string
  default = ""
}

variable "use_ec2" {
  type = bool
  default = false
}

# ========================================
# Azure 인증 정보
# ========================================
variable "azure_subscription_id" {
  description = "Azure Subscription ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "azure_tenant_id" {
  description = "Azure AD Tenant ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "azure_client_id" {
  description = "Azure Service Principal Client ID (Application ID)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "azure_client_secret" {
  description = "Azure Service Principal Client Secret (Password)"
  type        = string
  default     = ""
  sensitive   = true
}

# Azure 리소스 설정
variable "azure_resource_group" {
  description = "Azure Resource Group name"
  type        = string
  default     = "spot-tester-rg"
}

variable "azure_vnet_name" {
  description = "Azure Virtual Network name"
  type        = string
  default     = "spot-tester-vnet"
}

variable "azure_subnet_name" {
  description = "Azure Subnet name"
  type        = string
  default     = "default"
}

# Azure 테스트 설정
variable "azure_test_regions" {
  description = "List of Azure regions to test (RG, VNet, Subnet will be created by Terraform)"
  type        = list(string)
  default     = []
}

variable "azure_nic_pool_size_runtime" {
  description = "Actual number of NICs created via Python asyncio (Lambda 환경변수용)"
  type        = number
  default     = 50
}