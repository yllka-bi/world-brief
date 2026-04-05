# Create the IAM policy
resource "aws_iam_policy" "bedrock_combined_policy" {
  name        = "BedrockCombinedPolicy"
  description = "Policy combining S3, OpenSearch Serverless, and Bedrock permissions"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "OpenSearchServerlessAPIAccessAllStatement",
        "Effect" : "Allow",
        "Action" : [
          "aoss:APIAccessAll",
          "bedrock:InvokeModel"
        ],
        "Resource" : [
          "${aws_opensearchserverless_collection.forex_kb.arn}",
          "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
        ]
      }
    ]
  })
}

# Create the IAM role
resource "aws_iam_role" "bedrock_execution_role" {
  name = "${var.project_name}-AmazonBedrockExecutionRoleForKnowledgeBase-${var.environment}"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "bedrock.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
}

# Attach the policy to the role
resource "aws_iam_role_policy_attachment" "bedrock_policy_attachment" {
  role       = aws_iam_role.bedrock_execution_role.name
  policy_arn = aws_iam_policy.bedrock_combined_policy.arn
}
