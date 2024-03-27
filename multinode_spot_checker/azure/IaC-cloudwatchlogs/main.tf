resource "aws_cloudwatch_log_group" "spot_availability_tester_log_group" {
  name              = var.log_group_name
  retention_in_days = 90
}
