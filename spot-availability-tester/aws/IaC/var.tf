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

# must define exist cloudwatch log (from IaC-cloudwatch)
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