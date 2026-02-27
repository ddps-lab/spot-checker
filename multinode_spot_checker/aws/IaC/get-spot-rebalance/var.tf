variable "prefix" {
  type = string
  default = ""
}

variable "lambda_role_arn" {
  type = string
  default = ""
}

variable "log_group_name" {
  type = string
  default = ""
}

variable "log_stream_name_rebalance" {
  type = string
  default = ""
}
