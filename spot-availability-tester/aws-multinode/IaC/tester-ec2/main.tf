resource "aws_security_group" "tester_ec2_sg" {
  ingress = [{
    cidr_blocks      = ["0.0.0.0/0"]
    description      = ""
    from_port        = 22
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    protocol         = "tcp"
    security_groups  = []
    self             = false
    to_port          = 22
    }]
  egress = [{
    cidr_blocks      = ["0.0.0.0/0"]
    description      = ""
    from_port        = 0
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    protocol         = "-1"
    security_groups  = []
    self             = false
    to_port          = 0
  }]
  vpc_id = var.vpc_id

  tags = {
    "Name" = "${var.prefix}-${var.region}-ddd-tester-ec2-sg"
  }
}

resource "aws_instance" "tester_ec2" {
  ami                    = data.aws_ami.ubuntu_x86_ami.id
  instance_type          = "m5.large"
  iam_instance_profile   = var.iam_role
  subnet_id              = var.subnet_ids[0]
  vpc_security_group_ids = [aws_security_group.tester_ec2_sg.id]
  tags = {
    "Name" : "${var.prefix}-${var.region}-ddd-tester-ec2"
  }
  user_data = <<EOF
#!/bin/bash
sudo su
mkdir /ddd
chmod 777 /ddd -R
apt update && apt install golang -y
EOF
  root_block_device {
    volume_size           = 50    # 볼륨 크기를 지정합니다.
    volume_type           = "gp3" # 볼륨 유형을 지정합니다.
    delete_on_termination = true  # 인스턴스가 종료될 때 볼륨도 함께 삭제되도록 설정합니다.
  }
}