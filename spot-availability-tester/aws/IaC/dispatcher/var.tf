variable "prefix" {
  description = "Resource name prefix"
  type        = string
}

variable "worker_function_name" {
  description = "Worker Lambda function name to invoke"
  type        = string
}

variable "worker_function_arn" {
  description = "Worker Lambda function ARN"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM role ARN for Dispatcher Lambda"
  type        = string
}

variable "lambda_rate" {
  description = "EventBridge schedule expression (e.g., rate(1 minute))"
  type        = string
}
