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

module "get-spot-rebalance" {
  source                    = "./get-spot-rebalance"
  prefix                    = var.prefix
  lambda_role_arn           = aws_iam_role.get-spot-rebalance-lambda-role.arn
  log_group_name            = var.log_group_name
  log_stream_name_rebalance = var.log_stream_name_rebalance
}

module "get-spot-interruption" {
  source                       = "./get-spot-interruption"
  prefix                       = var.prefix
  lambda_role_arn              = aws_iam_role.get-spot-interruption-lambda-role.arn
  log_group_name               = var.log_group_name
  log_stream_name_interruption = var.log_stream_name_interruption
}

module "log-instance-count" {
  source                           = "./log-instance-count"
  prefix                           = var.prefix
  lambda_role_arn                  = aws_iam_role.log-instance-count-lambda-role.arn
  log_group_name                   = var.log_group_name
  log_stream_name_count            = var.log_stream_name_count
  log_stream_name_placement_failed = var.log_stream_name_placement_failed
  count_interval_minutes           = var.count_interval_minutes
  recent_window_minutes            = var.recent_window_minutes
}
