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

variable "log_stream_name_chage_status" {
  type = string
  default = ""
}

variable "log_stream_name_init_time" {
  type = string
  default = ""
}
variable "experiment_size" {
  type = string
  default = ""
}
