module "get-spot-status-change" {
  source                       = "./get-spot-status-change"
  prefix                       = var.prefix
  lambda_role_arn              = aws_iam_role.get-spot-status-change-lambda-role.arn
  log_group_name               = var.log_group_name
  log_stream_name_init_time    = var.log_stream_name_init_time
  log_stream_name_chage_status = var.log_stream_name_chage_status
}
module "restart-closed-request" {
  source                       = "./restart-closed-request"
  prefix                       = var.prefix
  lambda_role_arn              = aws_iam_role.restart-closed-request-lambda-role.arn
  log_group_name               = var.log_group_name
  experiment_size              = var.experiment_size
}
