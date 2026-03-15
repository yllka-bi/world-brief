resource "aws_ssm_parameter" "raw_bucket_name" {
  name        = "/${var.project_name}/${var.environment}/raw_bucket_name"
  description = "Name of the S3 raw bucket"
  type        = "String"
  value       = aws_s3_bucket.raw.id

  depends_on = [aws_s3_bucket.raw]
}

resource "aws_ssm_parameter" "raw_bucket_arn" {
  name        = "/${var.project_name}/${var.environment}/raw_bucket_arn"
  description = "ARN of the S3 raw bucket"
  type        = "String"
  value       = aws_s3_bucket.raw.arn

  depends_on = [aws_s3_bucket.raw]
}