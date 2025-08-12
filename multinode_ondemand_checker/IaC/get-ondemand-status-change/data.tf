data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "get-ondemand-status-change.py"
  output_path = "get-ondemand-status-change.zip"
}
