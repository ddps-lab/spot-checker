# terminate-no-name-instance는 최후에 삭제되도록 하고,
# 3분의 delay를 주고 삭제하도록 작성

module "vpc" {
  source = "./vpc"
  prefix = var.prefix
}

module "terminate-no-name-instances" {
  source = "./terminate-no-name-instance"
  prefix = var.prefix
  vpc_id = module.vpc.vpc_id
  lambda_role_arn = aws_iam_role.terminate-no-name-instance-lambda-role.arn
  log_group_name = var.log_group_name
  log_stream_name = var.terminate_log_stream_name
}

module "terminate-pending-instances" {
  source = "./terminate-pending-instance"
  prefix = var.prefix
  vpc_id = module.vpc.vpc_id
  lambda_role_arn = aws_iam_role.terminate-pending-instance-lambda-role.arn
  log_group_name = var.log_group_name
  log_stream_name = var.pending_log_stream_name
}

module "tester-ec2" {
  source = "./tester-ec2"
  prefix = var.prefix
  vpc_id = module.vpc.vpc_id
  subnet_ids = module.vpc.subnet_ids
  region = var.region
  iam_role = aws_iam_instance_profile.tester-ec2-role-instance-profile.name
  function_url = module.spot-availability-tester.function_url
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
