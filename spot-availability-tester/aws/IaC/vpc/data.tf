data "aws_region" "current_region" {}

data "aws_availability_zones" "region_azs" {
  state = "available"
  filter {
    name = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}