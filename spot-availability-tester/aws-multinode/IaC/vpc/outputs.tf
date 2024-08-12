output "vpc_id" {
  value = aws_vpc.spot_availability_tester_vpc.id
}

output "subnet_ids" {
  value = tolist(aws_subnet.spot_availability_tester_subnet[*].id)
}

output "subnet_az_names" {
  value = tolist(aws_subnet.spot_availability_tester_subnet[*].availability_zone)
}

output "security_group_id" {
  value = aws_security_group.spot_availability_tester_sg.id
}