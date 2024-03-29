resource "tls_private_key" "multinode-spot-key" {
  algorithm = "RSA"
  rsa_bits  = 4096
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
}

resource "azurerm_dev_test_global_vm_shutdown_schedule" "example" {
  count              = var.vm_count
  virtual_machine_id = azurerm_linux_virtual_machine.multinode-spot-vm[count.index].id
  location           = var.location
  enabled            = true

  daily_recurrence_time = var.time_minutes
  timezone              = "UTC"

  notification_settings {
    enabled = false
  }
}
