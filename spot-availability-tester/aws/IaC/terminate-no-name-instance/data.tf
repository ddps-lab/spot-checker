data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "terminate-no-name-instances.py"
  output_path = "terminate-no-name-instances.zip"
}
