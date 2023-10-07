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
variable "spot_availability_tester_log_group_name" {
  type = string
  default = ""
}

variable "terminate_no_name_instance_log_group_name" {
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

variable "instance_types" {
  type = list(string)
  default = []
}

variable "instance_types_az" {
  type = list(string)
  default = []
}