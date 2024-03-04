module "get-ondemand-status-change" {
  source                       = "./get-ondemand-status-change"
  prefix                       = var.prefix
  lambda_role_arn              = aws_iam_role.get-ondemand-status-change-lambda-role.arn
  log_group_name               = var.log_group_name
  log_stream_name_init_time    = var.log_stream_name_init_time
  log_stream_name_chage_status = var.log_stream_name_chage_status
}
