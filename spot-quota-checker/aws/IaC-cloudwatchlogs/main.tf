resource "aws_cloudwatch_log_group" "spot_availability_tester_log_group" {
  name              = var.log_group_name
  retention_in_days = 90
}

resource "aws_s3_bucket" "bucket" {
  bucket = "${var.prefix}-spot-quota-checker-log-${var.region}"
  force_destroy = true
}

resource "aws_s3_bucket_policy" "bucket_policy" {
  bucket = aws_s3_bucket.bucket.id

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "logs.${var.region}.amazonaws.com"
            },
            "Action": "s3:GetBucketAcl",
            "Resource": "arn:aws:s3:::${aws_s3_bucket.bucket.id}",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "${data.aws_caller_identity.current_account.account_id}"
                },
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:logs:${var.region}:${data.aws_caller_identity.current_account.account_id}:log-group:*"
                }
            }
        },
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "logs.${var.region}.amazonaws.com"
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::${aws_s3_bucket.bucket.id}/*",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "${data.aws_caller_identity.current_account.account_id}",
                    "s3:x-amz-acl": "bucket-owner-full-control"
                },
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:logs:${var.region}:${data.aws_caller_identity.current_account.account_id}:log-group:*"
                }
            }
        }
    ]
})
}