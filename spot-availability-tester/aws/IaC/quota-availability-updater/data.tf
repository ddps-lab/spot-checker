data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_dir = "./quota-availability-updater-src"
  output_path = "quota-availability-updater.zip"
}
