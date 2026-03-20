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

variable "log_stream_name_count" {
  type = string
  default = ""
}

variable "log_stream_name_placement_failed" {
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
