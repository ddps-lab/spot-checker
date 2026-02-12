resource "aws_cloudwatch_log_group" "lambda-cloudwatch-log-group" {
  name              = "/aws/lambda/${aws_lambda_function.lambda.function_name}"
  retention_in_days = 30
}

locals {
  subnet_ids      = jsonencode(var.subnet_ids)
  subnet_az_names = jsonencode(var.subnet_az_names)
}

resource "aws_lambda_function" "lambda" {
  function_name = "${var.prefix}-spot-availability-tester"
  architectures = ["x86_64"]
  memory_size   = 128
  timeout       = 60
  runtime       = "python3.11"
  handler       = var.use_ec2 ? "spot-availability-tester-ec2.lambda_handler" : "spot-availability-tester.lambda_handler"
  filename      = "spot-availability-tester.zip"
  role          = var.lambda_role_arn

  environment {
    variables = {
      X86_AMI_ID        = data.aws_ami.amazonlinux_2_x86_ami.id,
      ARM_AMI_ID        = data.aws_ami.amazonlinux_2_arm_ami.id,
      VPC_ID            = var.vpc_id,
      SUBNET_IDS        = local.subnet_ids,
      SUBNET_AZ_NAMES   = local.subnet_az_names,
      SECURITY_GROUP_ID = var.security_group_id,
      LOG_GROUP_NAME    = var.log_group_name,
      LOG_STREAM_NAME   = var.log_stream_name,
      PREFIX            = var.prefix
      DESCRIBE_RATE     = var.describe_rate
    }
  }
}

# EventBridge Rule ×N is replaced by dispatcher module
# When use_ec2 = false: dispatcher Lambda invokes this worker
# When use_ec2 = true: EC2 invokes via Function URL

resource "aws_lambda_function_url" "lambda-url" {
  function_name      = aws_lambda_function.lambda.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["*"]
    allow_headers = ["*"]
  }
}