resource "aws_ssm_parameter" "vpc_id" {
  name        = "/${var.project_name}/${var.environment}/vpc_id"
  description = "ID of the VPC"
  type        = "String"
  value       = aws_vpc.main.id

  depends_on = [aws_vpc.main]
}

resource "aws_ssm_parameter" "private_subnet_ids" {
  name        = "/${var.project_name}/${var.environment}/private_subnet_ids"
  description = "IDs of the private subnets (comma-separated)"
  type        = "StringList"
  value       = join(",", aws_subnet.private[*].id)

  depends_on = [aws_subnet.private]
}

resource "aws_ssm_parameter" "public_subnet_ids" {
  name        = "/${var.project_name}/${var.environment}/public_subnet_ids"
  description = "IDs of the public subnets (comma-separated)"
  type        = "StringList"
  value       = join(",", aws_subnet.public[*].id)

  depends_on = [aws_subnet.public]
}

resource "aws_ssm_parameter" "lambda_security_group_id" {
  name        = "/${var.project_name}/${var.environment}/lambda_security_group_id"
  description = "ID of the Lambda security group"
  type        = "String"
  value       = aws_security_group.lambda.id

  depends_on = [aws_security_group.lambda]
}

resource "aws_ssm_parameter" "s3_vpc_endpoint_id" {
  name        = "/${var.project_name}/${var.environment}/s3_vpc_endpoint_id"
  description = "ID of the S3 VPC endpoint"
  type        = "String"
  value       = aws_vpc_endpoint.s3.id

  depends_on = [aws_vpc_endpoint.s3]
}

resource "aws_ssm_parameter" "nat_gateway_id" {
  count       = var.enable_nat_gateway ? 1 : 0
  name        = "/${var.project_name}/${var.environment}/nat_gateway_id"
  description = "ID of the NAT Gateway (if enabled)"
  type        = "String"
  value       = aws_nat_gateway.main[0].id

  depends_on = [aws_nat_gateway.main]
}

resource "aws_ssm_parameter" "internet_gateway_id" {
  name        = "/${var.project_name}/${var.environment}/internet_gateway_id"
  description = "ID of the Internet Gateway"
  type        = "String"
  value       = aws_internet_gateway.main.id

  depends_on = [aws_internet_gateway.main]
}