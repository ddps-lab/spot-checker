provider "aws" {
  region  = var.region
  profile = var.awscli_profile
}

# Azure Provider 설정 (NIC 풀 생성용)
provider "azurerm" {
  features {}
  
  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
  client_id       = var.azure_client_id
  client_secret   = var.azure_client_secret
  
  skip_provider_registration = true
}
