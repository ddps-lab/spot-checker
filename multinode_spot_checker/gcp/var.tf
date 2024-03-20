variable "region" {
  type    = string
  default = ""
}

variable "zone" {
  type    = string
  default = ""
}

variable "prefix" {
  type = string
  default = ""
}


variable "instance_type" {
  type = string
  default = ""
}

variable "project_name" {
  type = string
  default = ""
}

variable "base_instance_name" {
  type = string
  default = ""
}
variable "target_size" {
  type = number
  default = 1
}
