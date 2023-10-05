data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "spot-availability-tester.py"
  output_path = "spot-availability-tester.zip"
}

data "aws_ami" "amazonlinux_2023_x86_ami" {
  most_recent = true
  filter {
    name   = "owner-alias"
    values = ["amazon"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

data "aws_ami" "amazonlinux_2023_arm_ami" {
  most_recent = true
  filter {
    name   = "owner-alias"
    values = ["amazon"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }
}