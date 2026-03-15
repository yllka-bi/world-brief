#####################################################
# DAILY NEWS SUMMARY LAMBDA FUNCTION
#####################################################

# Zip the prepared build directory
data "archive_file" "daily_news_zip" {
  type        = "zip"
  source_dir  = "${path.module}/build_daily_news"
  output_path = "${path.module}/daily_news.zip"
}

resource "aws_cloudwatch_log_group" "daily_news_lambda" {
  name              = "/aws/lambda/${var.project_name}-daily-news-${var.environment}"
  retention_in_days = var.log_retention
}

resource "aws_lambda_function" "daily_news" {
  filename         = data.archive_file.daily_news_zip.output_path
  function_name    = "${var.project_name}-daily-news-${var.environment}"
  role             = aws_iam_role.daily_news_lambda.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.daily_news_zip.output_base64sha256
  runtime          = "python3.12"
  memory_size      = 512
  timeout          = 300

  # Optional: Remove VPC config for faster cold starts and lower costs (Comprehend/SES work without VPC)
  # Uncomment if you need VPC access
  # vpc_config {
  #   subnet_ids         = var.private_subnet_ids
  #   security_group_ids = [var.lambda_security_group_id]
  # }

  environment {
    variables = {
      AWS_REGION       = var.aws_region
      RSS_FEED_URLS    = var.rss_feed_urls
      EMAIL_RECIPIENTS = var.email_recipients
      SENDER_EMAIL     = var.sender_email
      SCRAPERAPI_KEY   = jsondecode(data.aws_secretsmanager_secret_version.serpapi.secret_string)["SCRAPERAPI_KEY"]
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.daily_news_lambda,
    aws_iam_role_policy.daily_news_lambda
  ]
}

#####################################################
# EVENTBRIDGE SCHEDULER - Daily at 8 AM UTC
#####################################################

resource "aws_scheduler_schedule" "daily_news" {
  name       = "${var.project_name}-daily-news-schedule-${var.environment}"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "cron(0 8 * * ? *)" # 8:00 AM UTC daily

  target {
    arn      = aws_lambda_function.daily_news.arn
    role_arn = aws_iam_role.eventbridge_scheduler.arn
  }

  description = "Trigger daily news summary Lambda at 8 AM UTC"
}

# IAM role for EventBridge Scheduler to invoke Lambda
resource "aws_iam_role" "eventbridge_scheduler" {
  name = "${var.project_name}-eventbridge-scheduler-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_scheduler" {
  name = "${var.project_name}-eventbridge-scheduler-policy-${var.environment}"
  role = aws_iam_role.eventbridge_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.daily_news.arn
      }
    ]
  })
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "eventbridge_invoke" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.daily_news.function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.daily_news.arn
}
