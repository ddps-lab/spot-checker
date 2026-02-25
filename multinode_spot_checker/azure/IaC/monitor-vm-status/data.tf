data "archive_file" "monitor_vm_status_lambda" {
  type        = "zip"
  source_file = "${path.module}/../monitor-vm-status.py"
  output_path = "${path.module}/../monitor-vm-status.zip"
}

