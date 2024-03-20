resource "google_compute_instance_template" "spot_template" {
  name_prefix   = var.prefix
  machine_type  = var.instance_type

  scheduling {
    preemptible                 = true
    automatic_restart           = false
    provisioning_model          = "SPOT"
    instance_termination_action = "STOP"
  }

  disk {
    source_image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
    auto_delete  = true
    boot         = true
  }

  network_interface {
    network = "default"
  }
}

resource "google_compute_instance_group_manager" "spot_group" {
  name               = "spot-vm-group"
  version {
    instance_template = google_compute_instance_template.spot_template.id
  }

  base_instance_name = var.base_instance_name
  zone               = var.zone
  target_size        = var.target_size # 원하는 VM 인스턴스의 수
}