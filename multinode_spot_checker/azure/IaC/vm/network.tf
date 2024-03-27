resource "azurerm_virtual_network" "multinode-spot-network" {
  name                = "${var.prefix}-multinode-spot-network"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = ["192.168.0.0/16", "2001:db8::/48"]
}

resource "azurerm_subnet" "multinode-spot-subnet" {
  name                 = "${var.prefix}-multinode-spot-network-subnet"
  virtual_network_name = azurerm_virtual_network.multinode-spot-network.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = ["192.168.0.0/24", "2001:db8::/64"]
}

resource "azurerm_network_security_group" "multinode-spot-vm-sg" {
  name                = "${var.prefix}-multinode-spot-vm-sg"
  location            = var.location
  resource_group_name = var.resource_group_name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_public_ip" "multinode-spot-vm-public-ipv4" {
  count               = var.vm_count
  name                = "${var.prefix}-multinode-spot-vm-public-ipv4-${count.index}"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Dynamic"
  ip_version          = "IPv4"
}

resource "azurerm_network_interface" "multinode-spot-vm-nic" {
  count                         = var.vm_count
  name                          = "${var.prefix}-multinode-spot-vm-nic${count.index}"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  enable_accelerated_networking = true
  ip_configuration {
    primary                       = true
    name                          = "${var.prefix}-multinode-spot-vm-nic-ipv4"
    subnet_id                     = azurerm_subnet.multinode-spot-subnet.id
    private_ip_address_allocation = "Dynamic"
    private_ip_address_version    = "IPv4"
    public_ip_address_id          = azurerm_public_ip.multinode-spot-vm-public-ipv4[count.index].id
  }

  ip_configuration {
    name                          = "${var.prefix}-multinode-spot-vm-nic-ipv6"
    subnet_id                     = azurerm_subnet.multinode-spot-subnet.id
    private_ip_address_allocation = "Dynamic"
    private_ip_address_version    = "IPv6"
  }
}

resource "azurerm_network_interface_security_group_association" "multinode-spot-nic-sg-association" {
  count                     = var.vm_count
  network_interface_id      = azurerm_network_interface.multinode-spot-vm-nic[count.index].id
  network_security_group_id = azurerm_network_security_group.multinode-spot-vm-sg.id

  depends_on = [azurerm_network_interface.multinode-spot-vm-nic, azurerm_network_security_group.multinode-spot-vm-sg]
}
