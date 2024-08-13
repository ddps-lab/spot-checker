resource "aws_cloudwatch_log_group" "lambda-cloudwatch-log-group" {
  name              = "/aws/lambda/${aws_lambda_function.lambda.function_name}"
  retention_in_days = 30
}

locals {
  subnet_ids = jsonencode(var.subnet_ids)
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
      SUBNET_AZ_NAMES        = local.subnet_az_names,
      SECURITY_GROUP_ID = var.security_group_id,
      LOG_GROUP_NAME    = var.log_group_name,
      LOG_STREAM_NAME   = var.log_stream_name,
      PREFIX = var.prefix
      DESCRIBE_RATE = var.describe_rate
    }
  }
}

# # EventBridge Rule
resource "aws_cloudwatch_event_rule" "eventbridge-rule" {
  count               = var.use_ec2 ? 0 : length(var.instance_types)
  name                = "${var.prefix}-${var.instance_types[count.index]}-${var.instance_types_az[count.index]}-rule"
  schedule_expression = var.lambda_rate
  depends_on          = [aws_lambda_function.lambda]
}

# Target for EventBridge to trigger Lambda
resource "aws_cloudwatch_event_target" "eventbridge-target" {
  count     = var.use_ec2 ? 0 : length(var.instance_types)
  rule      = aws_cloudwatch_event_rule.eventbridge-rule[count.index].name
  target_id = "${var.prefix}-${var.instance_types[count.index]}-${var.instance_types_az[count.index]}-target"
  input     = <<EOF
{
  "instance_type": "${var.instance_types[count.index]}",
  "availability_zone": "${var.instance_types_az[count.index]}"
}
EOF
  arn       = aws_lambda_function.lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_rw_fallout_retry_step_deletion_lambda" {
  count         = var.use_ec2 ? 0 : length(var.instance_types)
  statement_id  = "${replace(var.instance_types[count.index], ".", "_")}-${var.instance_types_az[count.index]}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.eventbridge-rule[count.index].arn
}

resource "aws_lambda_function_url" "lambda-url" {
  function_name      = aws_lambda_function.lambda.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = [ "*" ]
    allow_methods = [ "*" ]
    allow_headers = [ "*" ]
  }
}