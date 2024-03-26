data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "get-spot-status-change.py"
  output_path = "get-spot-status-change.zip"
}
