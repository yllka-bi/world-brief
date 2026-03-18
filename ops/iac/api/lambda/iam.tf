#####################################################
# DAILY NEWS SUMMARY LAMBDA IAM
#####################################################
resource "aws_iam_role" "daily_news_lambda" {
  name = "${var.project_name}-daily-news-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "daily_news_lambda" {
  name = "${var.project_name}-daily-news-lambda-policy-${var.environment}"
  role = aws_iam_role.daily_news_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-daily-news-${var.environment}:*"
      },
      {
        Sid    = "AmazonComprehendAccess"
        Effect = "Allow"
        Action = [
          "comprehend:DetectSentiment",
          "comprehend:DetectKeyPhrases",
          "comprehend:DetectEntities",
          "comprehend:BatchDetectSentiment",
          "comprehend:BatchDetectKeyPhrases",
          "comprehend:BatchDetectEntities"
        ]
        Resource = "*"
      },
      {
        Sid    = "AmazonSESAccess"
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      },
      {
        Sid    = "AmazonBedrockAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      {
        Sid    = "DynamoDBEntityTrends"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = "arn:aws:dynamodb:${var.aws_region}:*:table/${var.project_name}-entity-trends-${var.environment}"
      },
      {
        Sid    = "ReadSecretsManager"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "*"
      }
    ]
  })
}
