# terminate-no-name-instance는 최후에 삭제되도록 하고,
# 3분의 delay를 주고 삭제하도록 작성

module "vpc" {
  source = "./vpc"
  prefix = var.prefix
}

module "terminate-no-name-instances" {
  source = "./terminate-no-name-instance"
  prefix = var.prefix
  lambda_role_arn = aws_iam_role.terminate-no-name-instance-lambda-role.arn
  log_group_name = var.log_group_name
  log_stream_name = var.terminate_log_stream_name
}

module "terminate-pending-instances" {
  source = "./terminate-pending-instance"
  prefix = var.prefix
  lambda_role_arn = aws_iam_role.terminate-pending-instance-lambda-role.arn
  log_group_name = var.log_group_name
  log_stream_name = var.pending_log_stream_name
}

module "spot-availability-tester" {
  source = "./spot-availability-tester"
  prefix = var.prefix
  lambda_role_arn = aws_iam_role.spot-availability-tester-lambda-role.arn
  vpc_id = module.vpc.vpc_id
  subnet_ids = module.vpc.subnet_ids
  subnet_az_names = module.vpc.subnet_az_names
  security_group_id = module.vpc.security_group_id
  instance_types = var.instance_types
  instance_types_az = var.instance_types_az
  log_group_name = var.log_group_name
  log_stream_name = var.spot_log_stream_name
  lambda_rate = var.lambda_rate
}

module "quota-availability-updater" {
  source = "./quota-availability-updater"
  prefix = var.prefix
  lambda_role_arn = aws_iam_role.quota-availability-updater-lambda-role.arn
  region = var.region
}

resource "aws_dynamodb_table" "DDDCHECKTABLE" {
  name           = "${var.prefix}-DDDCHECKTABLE"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "TABLE"

  attribute {
    name = "TABLE"
    type = "N"  # string
  }
}
