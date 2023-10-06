output "vpc_id" {
  value = aws_vpc.spot_availability_tester_vpc.id
}

output "subnet_ids" {
  value = tolist(aws_subnet.spot_availability_tester_subnet[*].id)
}

output "security_group_id" {
  value = aws_security_group.spot_availability_tester_sg.id
}