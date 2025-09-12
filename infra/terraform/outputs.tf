output "uploads_bucket_name" { value = aws_s3_bucket.uploads.bucket }
output "uploads_bucket_arn"  { value = aws_s3_bucket.uploads.arn }
output "kms_key_id"          { value = aws_kms_key.uploads.id }
output "kms_key_arn"         { value = aws_kms_key.uploads.arn }
