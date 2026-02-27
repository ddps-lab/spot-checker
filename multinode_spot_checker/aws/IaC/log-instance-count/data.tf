data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "log-instance-count.py"
  output_path = "log-instance-count.zip"
}
