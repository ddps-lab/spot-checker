# S3 버킷 (CloudWatch Logs Export용)
resource "aws_s3_bucket" "logs_export" {
  bucket        = "${var.prefix}-logs-export"
  force_destroy = true  # destroy 시 버킷 내용물과 함께 삭제
}

# S3 버킷 정책 (CloudWatch Logs가 쓸 수 있도록)
resource "aws_s3_bucket_policy" "logs_export_policy" {
  bucket = aws_s3_bucket.logs_export.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSLogDeliveryAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.region}.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.logs_export.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current_account.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current_account.account_id}:log-group:*"
          }
        }
      },
      {
        Sid    = "AWSLogDeliveryWrite"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.region}.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.logs_export.arn}/*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current_account.account_id
            "s3:x-amz-acl"      = "bucket-owner-full-control"
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current_account.account_id}:log-group:*"
          }
        }
      }
    ]
  })
}

# S3 버킷 수명 주기 (30일 후 자동 삭제)
resource "aws_s3_bucket_lifecycle_configuration" "logs_export_lifecycle" {
  bucket = aws_s3_bucket.logs_export.id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    expiration {
      days = 30
    }
  }
}

# S3 버킷 암호화
resource "aws_s3_bucket_server_side_encryption_configuration" "logs_export_encryption" {
  bucket = aws_s3_bucket.logs_export.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 버킷 버전 관리 비활성화 (로그는 버전 관리 불필요)
resource "aws_s3_bucket_versioning" "logs_export_versioning" {
  bucket = aws_s3_bucket.logs_export.id

  versioning_configuration {
    status = "Disabled"
  }
}

# 출력
output "s3_bucket_name" {
  value       = aws_s3_bucket.logs_export.id
  description = "S3 bucket name for CloudWatch Logs export"
}

output "s3_bucket_arn" {
  value       = aws_s3_bucket.logs_export.arn
  description = "S3 bucket ARN for CloudWatch Logs export"
}

