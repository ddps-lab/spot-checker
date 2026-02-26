# ============================================================
# Module instantiations for aws-v2 Lambda functions
# ============================================================

module "get-spot-status-change" {
  source = "./modules/get-spot-status-change"

  prefix                       = var.prefix
  lambda_role_arn              = aws_iam_role.get-spot-status-change-role.arn
  log_group_name               = var.log_group_name
  log_stream_name_chage_status = var.log_stream_name_chage_status
  log_stream_name_init_time    = var.log_stream_name_init_time
}

module "restart-closed-request" {
  source = "./modules/restart-closed-request"

  prefix                   = var.prefix
  lambda_role_arn          = aws_iam_role.restart-closed-request-role.arn
  log_group_name           = var.log_group_name
  experiment_size          = var.experiment_size
  iam_instance_profile_arn = var.iam_instance_profile_arn
}

module "get-spot-rebalance" {
  source = "./modules/get-spot-rebalance"

  prefix                    = var.prefix
  lambda_role_arn           = aws_iam_role.get-spot-rebalance-role.arn
  log_group_name            = var.log_group_name
  log_stream_name_rebalance = var.log_stream_name_rebalance
}

module "get-spot-interruption" {
  source = "./modules/get-spot-interruption"

  prefix                       = var.prefix
  lambda_role_arn              = aws_iam_role.get-spot-interruption-role.arn
  log_group_name               = var.log_group_name
  log_stream_name_interruption = var.log_stream_name_interruption
}

module "log-instance-count" {
  source = "./modules/log-instance-count"

  prefix                           = var.prefix
  lambda_role_arn                  = aws_iam_role.log-instance-count-role.arn
  log_group_name                   = var.log_group_name
  log_stream_name_count            = var.log_stream_name_count
  log_stream_name_placement_failed = var.log_stream_name_placement_failed
  count_interval_minutes           = var.count_interval_minutes
  recent_window_minutes            = var.recent_window_minutes
}
