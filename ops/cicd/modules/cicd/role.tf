resource "aws_iam_role" "project_role" {
  name = var.role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = [
            "quicksight.amazonaws.com",
            "codebuild.amazonaws.com",
            "codepipeline.amazonaws.com"
          ]
        },
        Action = "sts:AssumeRole"
      }
    ]
  })  
}

resource "aws_iam_role_policy" "project_role_policy" {
  role = aws_iam_role.project_role.name

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeDhcpOptions",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeVpcs",
          "ec2:ModifyNetworkInterfaceAttribute",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "ecr:*",
          "secretsmanager:GetSecretValue",
          "ssm:GetParameters",
          "s3:*",
          "codestar-connections:UseConnection",
          "codebuild:BatchGetBuilds",
          "codebuild:StartBuild"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = "s3:*",
        Resource = [
          "${aws_s3_bucket.cicd_storage_bucket.arn}",
          "${aws_s3_bucket.cicd_storage_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = "codestar-connections:UseConnection",
        Resource = "${aws_codestarconnections_connection.connection.arn}"
      }
    ]
  })
}
