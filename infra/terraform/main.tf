locals {
  bucket_name = var.uploads_bucket_name != null ? var.uploads_bucket_name : "${var.project}-${var.env}-uploads"
}

# KMS CMK for S3 encryption
resource "aws_kms_key" "uploads" {
  description             = "KMS CMK for ${local.bucket_name}"
  enable_key_rotation     = true
  deletion_window_in_days = 7
}

resource "aws_kms_alias" "uploads" {
  name          = "alias/${local.bucket_name}"
  target_key_id = aws_kms_key.uploads.id
}

# S3 bucket
resource "aws_s3_bucket" "uploads" {
  bucket        = local.bucket_name
  force_destroy = false
}

# Block public access
resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = aws_s3_bucket.uploads.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# Versioning (optional but handy)
resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  versioning_configuration { status = "Enabled" }
}

# Default encryption (SSE-KMS)
resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.uploads.arn
    }
    bucket_key_enabled = true
  }
}

# TLS-only bucket policy
resource "aws_s3_bucket_policy" "uploads_tls_only" {
  bucket = aws_s3_bucket.uploads.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid: "DenyInsecureTransport",
        Effect: "Deny",
        Principal: "*",
        Action: "s3:*",
        Resource: [
          aws_s3_bucket.uploads.arn,
          "${aws_s3_bucket.uploads.arn}/*"
        ],
        Condition: { Bool: { "aws:SecureTransport": "false" } }
      }
    ]
  })
}

# CORS for browser -> S3 presigned POST
resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  cors_rule {
    allowed_methods = ["POST"]
    allowed_origins = var.cors_allowed_origins
    allowed_headers = ["*"]
    expose_headers  = ["ETag", "x-amz-request-id"]
    max_age_seconds = 3000
  }
}
