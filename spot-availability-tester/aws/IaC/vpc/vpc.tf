resource "aws_vpc" "spot_availability_tester_vpc" {
  cidr_block           = "192.168.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.prefix}-spot-availability-tester-vpc"
  }
}

resource "aws_internet_gateway" "spot_availability_tester_igw" {
  vpc_id   = aws_vpc.spot_availability_tester_vpc.id
  tags = {
    Name = "${var.prefix}-spot-availability-tester-igw"
  }
}

resource "aws_subnet" "spot_availability_tester_subnet" {
  vpc_id            = aws_vpc.spot_availability_tester_vpc.id
  count             = length(data.aws_availability_zones.region_azs.names)
  cidr_block        = "192.168.${count.index}.0/24"
  availability_zone = data.aws_availability_zones.region_azs.names[count.index]
  enable_resource_name_dns_a_record_on_launch = true
  map_public_ip_on_launch = true
  tags = {
    "Name" : "${var.prefix}-spot-availability-tester-subnet-${substr(data.aws_availability_zones.region_azs.names[count.index], -1, 1)}"
  }
}


resource "aws_route_table" "spot_availability_tester_route_table" {
  vpc_id = aws_vpc.spot_availability_tester_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.spot_availability_tester_igw.id
  }
  route {
    ipv6_cidr_block = "::/0"
    gateway_id      = aws_internet_gateway.spot_availability_tester_igw.id
  }
  tags = {
    "Name" : "${var.prefix}-spot-availability-tester-vpc-public-route-table"
  }
}

resource "aws_route_table_association" "spot_availability_tester_route_table_association" {
  count          = length(aws_subnet.spot_availability_tester_subnet)
  subnet_id      = aws_subnet.spot_availability_tester_subnet[count.index].id
  route_table_id = aws_route_table.spot_availability_tester_route_table.id
}

resource "aws_security_group" "spot_availability_tester_sg" {
  ingress = [{
    cidr_blocks      = [aws_vpc.spot_availability_tester_vpc.cidr_block]
    description      = "same vpc allow"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
    }, {
    cidr_blocks      = ["0.0.0.0/0"]
    description      = "SSH allow"
    from_port        = 0
    to_port          = 22
    protocol         = "tcp"
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }]

  egress = [{
    cidr_blocks      = ["0.0.0.0/0"]
    description      = "alow all outbound"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }]
  vpc_id = aws_vpc.spot_availability_tester_vpc.id

  tags = {
    "Name" = "${var.prefix}-spot-availability-tester-sg"
  }
}