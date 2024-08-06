data "archive_file" "lambda_source_code" {
  type        = "zip"
  source_file = "spot-availability-tester.py"
  output_path = "spot-availability-tester.zip"
}

data "aws_ami" "amazonlinux_2_arm_ami" {
  most_recent = true
  owners = ["amazon"]

  filter {
    name   = "architecture"
    values = ["arm64"]
  }

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm*gp2"]
  }
}

data "aws_ami" "amazonlinux_2_x86_ami" {
  most_recent = true
  owners = ["amazon"]

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm*gp2"]
  }
}
