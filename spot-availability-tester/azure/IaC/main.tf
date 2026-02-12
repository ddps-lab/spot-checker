# terminate-no-name-instance는 최후에 삭제되도록 하고,
# 3분의 delay를 주고 삭제하도록 작성

module "vpc" {
  source = "./vpc"
  prefix = var.prefix
}

module "terminate-orphan-disk" {
  source = "./terminate-orphan-disk"
  prefix = var.prefix
  lambda_role_arn = aws_iam_role.terminate-orphan-disk-lambda-role.arn
  log_group_name = var.log_group_name
  log_stream_name = var.terminate_log_stream_name
  
  # Azure 인증 정보
  azure_subscription_id = var.azure_subscription_id
  azure_tenant_id       = var.azure_tenant_id
  azure_client_id       = var.azure_client_id
  azure_client_secret   = var.azure_client_secret
  azure_region          = length(var.azure_test_regions) > 0 ? var.azure_test_regions[0] : "US West 3"
  
  # Lambda Layer
  azure_sdk_layer_arn   = aws_lambda_layer_version.azure_sdk_layer.arn
}

module "terminate-failed-vms" {
  source = "./terminate-failed-vms"
  prefix = var.prefix
  lambda_role_arn = aws_iam_role.terminate-failed-vms-lambda-role.arn
  log_group_name = var.log_group_name
  log_stream_name = var.pending_log_stream_name
  
  # Azure 인증 정보
  azure_subscription_id = var.azure_subscription_id
  azure_tenant_id       = var.azure_tenant_id
  azure_client_id       = var.azure_client_id
  azure_client_secret   = var.azure_client_secret
  azure_region          = length(var.azure_test_regions) > 0 ? var.azure_test_regions[0] : "US West 3"
  
  # Lambda Layer
  azure_sdk_layer_arn   = aws_lambda_layer_version.azure_sdk_layer.arn
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
  use_ec2 = var.use_ec2
  describe_rate = var.describe_rate
  
  # Azure 인증 정보
  azure_subscription_id = var.azure_subscription_id
  azure_tenant_id       = var.azure_tenant_id
  azure_client_id            = var.azure_client_id
  azure_client_secret        = var.azure_client_secret
  azure_nic_pool_size_runtime = var.azure_nic_pool_size_runtime
  
  # Lambda Layer
  azure_sdk_layer_arn   = aws_lambda_layer_version.azure_sdk_layer.arn
}

module "tester-ec2" {
  source = "./tester-ec2"
  count = var.use_ec2 ? 1 : 0
  prefix = var.prefix
  vpc_id = module.vpc.vpc_id
  subnet_ids = module.vpc.subnet_ids
  region = var.region
  iam_role = aws_iam_instance_profile.tester-ec2-role-instance-profile.name
  function_url = module.spot-availability-tester.function_url
}

