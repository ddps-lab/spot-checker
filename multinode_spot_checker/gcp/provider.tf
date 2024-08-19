provider "google" {
  credentials = file("./credential.json")
  project = var.project_name
  region  = var.region
  zone    = var.zone
}