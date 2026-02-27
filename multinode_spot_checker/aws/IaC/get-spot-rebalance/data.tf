data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "get-spot-rebalance.py"
  output_path = "get-spot-rebalance.zip"
}
