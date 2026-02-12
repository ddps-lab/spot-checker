data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "terminate-pending-instances.py"
  output_path = "terminate-pending-instances.zip"
}
