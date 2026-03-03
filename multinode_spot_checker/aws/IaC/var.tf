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

variable "log_stream_name_change_status" {
  type = string
  default = ""
}

variable "log_stream_name_init_time" {
  type = string
  default = ""
}

variable "log_stream_name_rebalance" {
  type = string
  default = ""
}

variable "log_stream_name_interruption" {
  type = string
  default = ""
}

variable "log_stream_name_count" {
  type = string
  default = ""
}

variable "log_stream_name_placement_failed" {
  type = string
  default = ""
}

variable "experiment_size" {
  type = string
  default = ""
}

variable "count_interval_minutes" {
  type = string
  default = "1"
}

variable "recent_window_minutes" {
  type = string
  default = "10"
}

variable "iam_instance_profile_arn" {
  type = string
  default = ""
}
