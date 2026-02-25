# 현재 AWS 계정 정보
data "aws_caller_identity" "current_account" {}

# 현재 AWS 리전
data "aws_region" "current" {}

