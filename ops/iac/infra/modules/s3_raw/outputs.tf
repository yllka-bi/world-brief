output "raw_bucket_name" {
  description = "Name of the S3 raw bucket"
  value       = aws_s3_bucket.raw.id
}

output "raw_bucket_arn" {
  description = "ARN of the S3 raw bucket"
  value       = aws_s3_bucket.raw.arn
}

output "s3_file_storage" {
  description = "Name of the S3 file storage bucket"
  value       = aws_s3_bucket.s3_file_storage.arn
}