data "aws_secretsmanager_secret" "serpapi" {
  name = "/${var.project_name}/${var.environment}/serpapi/"
}

data "aws_secretsmanager_secret_version" "serpapi" {
  secret_id = data.aws_secretsmanager_secret.serpapi.id
}
