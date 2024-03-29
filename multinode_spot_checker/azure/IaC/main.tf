resource "azurerm_resource_group" "multinode-spot-resource-group" {
  name     = var.resource_group_name
  location = var.location
}

module "vm" {
  source              = "./vm"
  azurecli_user_id    = var.azurecli_user_id
  prefix              = var.prefix
  location            = var.location
  resource_group_name = var.resource_group_name
  ssh-username        = var.prefix
  ssh-keyname         = "${var.prefix}-sshkey"
  vm_count            = var.vm_count
  vm_size             = var.vm_size
  depends_on          = [azurerm_resource_group.multinode-spot-resource-group]
  time_minutes        = var.time_minutes
}
