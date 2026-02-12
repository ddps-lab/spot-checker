# Azure 리소스 생성 (RG, VNet, Subnet, NSG)
# NIC는 Python asyncio로 생성 (create_tester.py)
# terraform destroy 시 모두 삭제됨

locals {
  # Azure Region 매핑 (CSV Region → Azure API Region)
  azure_region_map = {
    "US East"           = "eastus"
    "US East 2"         = "eastus2"
    "US West"           = "westus"
    "US West 2"         = "westus2"
    "US West 3"         = "westus3"
    "US Central"        = "centralus"
    "US North Central"  = "northcentralus"
    "US South Central"  = "southcentralus"
    "US West Central"   = "westcentralus"
    "CA Central"        = "canadacentral"
    "CA East"           = "canadaeast"
    "BR South"          = "brazilsouth"
    "CL Central"        = "chilecentral"
    "MX Central"        = "mexicocentral"
    "EU North"          = "northeurope"
    "EU West"           = "westeurope"
    "UK South"          = "uksouth"
    "UK West"           = "ukwest"
    "FR Central"        = "francecentral"
    "FR South"          = "francesouth"
    "DE West Central"   = "germanywestcentral"
    "CH North"          = "switzerlandnorth"
    "CH West"           = "switzerlandwest"
    "NO East"           = "norwayeast"
    "NO West"           = "norwaywest"
    "SE Central"        = "swedencentral"
    "PL Central"        = "polandcentral"
    "IT North"          = "italynorth"
    "ES Central"        = "spaincentral"
    "AT East"           = "austriaeast"
    "GR Central"        = "greececentral"
    "IL Central"        = "israelcentral"
    "QA Central"        = "qatarcentral"
    "AE Central"        = "uaecentral"
    "AE North"          = "uaenorth"
    "ZA North"          = "southafricanorth"
    "ZA West"           = "southafricawest"
    "IN Central"        = "centralindia"
    "IN South"          = "southindia"
    "IN West"           = "westindia"
    "JA East"           = "japaneast"
    "JA West"           = "japanwest"
    "KR Central"        = "koreacentral"
    "KR South"          = "koreasouth"
    "AU East"           = "australiaeast"
    "AU Southeast"      = "australiasoutheast"
    "AU Central"        = "australiacentral"
    "AU Central 2"      = "australiacentral2"
    "NZ North"          = "newzealandnorth"
    "AP East"           = "eastasia"
    "AP Southeast"      = "southeastasia"
    "ID Central"        = "indonesiacentral"
    "CN East"           = "chinaeast"
    "CN East 2"         = "chinaeast2"
    "CN East 3"         = "chinaeast3"
    "CN North"          = "chinanorth"
    "CN North 2"        = "chinanorth2"
    "CN North 3"        = "chinanorth3"
  }
  
  # Region별로 그룹화 (Resource Group, VNet, Subnet 생성용)
  unique_regions = {
    for region in var.azure_test_regions :
    region => lookup(local.azure_region_map, region, lower(replace(region, " ", "")))
  }
}

# ========================================
# Resource Group (각 region별)
# ========================================
resource "azurerm_resource_group" "spot_tester" {
  for_each = local.unique_regions
  
  name     = "${var.prefix}-${replace(each.key, " ", "-")}-rg"
  location = each.value
  
  tags = {
    Environment = "spot-tester"
    ManagedBy   = "terraform"
    Purpose     = "azure-spot-availability-testing"
  }
}

# ========================================
# Virtual Network (각 region별)
# ========================================
resource "azurerm_virtual_network" "spot_tester" {
  for_each = local.unique_regions
  
  name                = "${var.prefix}-${replace(each.key, " ", "-")}-vnet"
  location            = each.value
  resource_group_name = azurerm_resource_group.spot_tester[each.key].name
  address_space       = ["10.0.0.0/16"]
  
  tags = {
    Environment = "spot-tester"
    ManagedBy   = "terraform"
  }
}

# ========================================
# Subnet (각 region별)
# ========================================
resource "azurerm_subnet" "spot_tester" {
  for_each = local.unique_regions
  
  name                 = "default"
  resource_group_name  = azurerm_resource_group.spot_tester[each.key].name
  virtual_network_name = azurerm_virtual_network.spot_tester[each.key].name
  address_prefixes     = ["10.0.1.0/24"]
}

# ========================================
# Network Security Group (각 region별)
# ========================================
resource "azurerm_network_security_group" "spot_tester" {
  for_each = local.unique_regions
  
  name                = "${var.prefix}-${replace(each.key, " ", "-")}-nsg"
  location            = each.value
  resource_group_name = azurerm_resource_group.spot_tester[each.key].name
  
  security_rule {
    name                       = "AllowOutbound"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
  
  tags = {
    Environment = "spot-tester"
    ManagedBy   = "terraform"
  }
}

# ========================================
# Network Interface는 Python asyncio로 생성 (create_tester.py)
# - 훨씬 빠른 병렬 처리 (7-15배 빠름)
# - terraform destroy 시 Resource Group과 함께 자동 삭제
# ========================================

# ========================================
# Subnet과 NSG 연결
# ========================================
resource "azurerm_subnet_network_security_group_association" "spot_tester" {
  for_each = local.unique_regions
  
  subnet_id                 = azurerm_subnet.spot_tester[each.key].id
  network_security_group_id = azurerm_network_security_group.spot_tester[each.key].id
}

# ========================================
# Output (생성된 리소스 정보)
# ========================================
output "azure_resource_groups" {
  description = "생성된 Azure Resource Group 정보"
  value = {
    for k, v in azurerm_resource_group.spot_tester :
    k => {
      id       = v.id
      name     = v.name
      location = v.location
    }
  }
}
