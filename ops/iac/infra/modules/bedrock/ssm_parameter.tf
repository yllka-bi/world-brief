resource "aws_ssm_parameter" "opensearch_collection_endpoint" {
  name        = "/${var.project_name}/${var.environment}/opensearch/collection_endpoint"
  description = "OpenSearch Serverless collection endpoint"
  type        = "String"
  value       = aws_opensearchserverless_collection.forex_kb.collection_endpoint
}

resource "aws_ssm_parameter" "bedrock_kb_id" {
  name        = "/${var.project_name}/${var.environment}/bedrock/knowledge_base_id"
  description = "Bedrock Knowledge Base ID"
  type        = "String"
  value       = aws_bedrockagent_knowledge_base.bedrock_kb.id
}

resource "aws_ssm_parameter" "bedrock_data_source_id" {
  name        = "/${var.project_name}/${var.environment}/bedrock/data_source_id"
  description = "Bedrock Knowledge Base Data Source ID"
  type        = "String"
  value       = aws_bedrockagent_data_source.example.data_source_id
}
