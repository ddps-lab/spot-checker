variable "azurecli_user_id" {
  type    = string
  default = ""
}

variable "location" {
  type    = string
  default = ""
}

variable "prefix" {
  type    = string
  default = ""
}

variable "resource_group_name" {
  type    = string
  default = ""
}

variable "vm_count" {
  type    = number
  default = 1
}

variable "vm_size" {
  type    = string
  default = ""
}
