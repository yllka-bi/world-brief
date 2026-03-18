resource "aws_iam_user" "codepipeline_user" {
  name = "${var.project_name}-deployment-user-${var.environment}"
  tags = {
    Purpose = "Used by CodePipeline for ${var.project_name} in ${var.environment}"
  }
}

resource "aws_iam_access_key" "codepipeline_key" {
  user = aws_iam_user.codepipeline_user.name
}
resource "aws_iam_user_policy_attachment" "policy_attachments" {
  for_each   = toset(local.policy_arns)
  user       = aws_iam_user.codepipeline_user.name
  policy_arn = each.value
}
locals {
  policy_arns = [
    "arn:aws:iam::aws:policy/AdministratorAccess",
    // To be determined based on project needs
    # "arn:aws:iam::aws:policy/AWSCodeCommitFullAccess",
    # "arn:aws:iam::aws:policy/AWSCodeBuildAdminAccess",
    # "arn:aws:iam::aws:policy/AmazonS3FullAccess",
    # "arn:aws:iam::aws:policy/AWSLambda_FullAccess",
    # "arn:aws:iam::aws:policy/CloudWatchFullAccess"
  ]
}



resource "aws_secretsmanager_secret" "codepipeline_secret" {
  name = "${var.project_name}-codepipeline/deployment-user-${var.environment}"
  description = "Access key for deployment-user used by CodePipeline"
}

resource "aws_secretsmanager_secret_version" "codepipeline_secret_version" {
  secret_id     = aws_secretsmanager_secret.codepipeline_secret.id
  secret_string = jsonencode({
    aws_access_key_id     = aws_iam_access_key.codepipeline_key.id
    aws_secret_access_key = aws_iam_access_key.codepipeline_key.secret
  })
}