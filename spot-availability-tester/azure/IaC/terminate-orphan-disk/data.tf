data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "terminate-orphan-disks.py"
  output_path = "terminate-orphan-disks.zip"
}
