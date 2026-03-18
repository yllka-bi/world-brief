# Lambda Module Output values
output "lambda_name" {
  description = "Name of the daily news Lambda function"
  value       = aws_lambda_function.daily_news.function_name
}

output "lambda_role_arn" {
  description = "ARN of the daily news Lambda IAM role"
  value       = aws_iam_role.daily_news_lambda.arn
}

output "lambda_function_arn" {
  description = "ARN of the daily news Lambda function"
  value       = aws_lambda_function.daily_news.arn
}

output "lambda_function_invoke_arn" {
  description = "Invoke ARN of the daily news Lambda function"
  value       = aws_lambda_function.daily_news.invoke_arn
}

output "scheduler_arn" {
  description = "ARN of the EventBridge Scheduler"
  value       = aws_scheduler_schedule.daily_news.arn
}