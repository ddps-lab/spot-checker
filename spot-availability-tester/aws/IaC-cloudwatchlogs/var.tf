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

variable "spot_availability_tester_log_group_name" {
  type = string
  default = ""
}

variable "terminate_no_name_instance_log_group_name" {
  type = string
  default = ""
}