data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "get-spot-interruption.py"
  output_path = "get-spot-interruption.zip"
}
