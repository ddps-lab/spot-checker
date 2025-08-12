data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "restart-closed-request.py"
  output_path = "restart-closed-request.zip"
}
