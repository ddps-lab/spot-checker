# Azure SDK Lambda Layer
# Azure 관리를 위한 Python SDK 패키지

resource "aws_lambda_layer_version" "azure_sdk_layer" {
  filename            = "azure_sdk_layer.zip"
  layer_name          = "${var.prefix}-azure-sdk-layer"
  compatible_runtimes = ["python3.11"]
  
  description = "Azure SDK for Python: azure-identity, azure-mgmt-compute, azure-mgmt-network, azure-mgmt-resource"
}

output "azure_sdk_layer_arn" {
  value       = aws_lambda_layer_version.azure_sdk_layer.arn
  description = "ARN of the Azure SDK Lambda Layer"
}

