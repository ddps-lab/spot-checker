resource "tls_private_key" "multinode-spot-key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "azurerm_storage_account" "multinode-spot-sta" {
  name                     = "${var.prefix}sga"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_linux_virtual_machine" "multinode-spot-vm" {
  count                 = var.vm_count
  name                  = "${var.prefix}-vm-${count.index}"
  resource_group_name   = var.resource_group_name
  location              = var.location
  size                  = var.vm_size
  admin_username        = var.ssh-username
  network_interface_ids = [element(azurerm_network_interface.multinode-spot-vm-nic.*.id, count.index)]

  custom_data = filebase64("./vm/custom_data.tpl")

  admin_ssh_key {
    username   = var.ssh-username
    public_key = tls_private_key.multinode-spot-key.public_key_openssh
  }

  priority        = "Spot"
  eviction_policy = "Delete"

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb         = 64
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-focal"
    sku       = "20_04-lts-gen2"
    version   = "latest"
  }

  boot_diagnostics {
    storage_account_uri = azurerm_storage_account.multinode-spot-sta.primary_blob_endpoint
  }
}
