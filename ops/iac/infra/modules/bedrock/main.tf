resource "aws_opensearchserverless_collection" "forex_kb" {
  name = var.kb_oss_collection_name
  type = "VECTORSEARCH"
  depends_on = [
    aws_opensearchserverless_access_policy.forex_kb,
    aws_opensearchserverless_security_policy.forex_kb_encryption,
    aws_opensearchserverless_security_policy.forex_kb_network
  ]
}
resource "aws_bedrockagent_knowledge_base" "bedrock_kb" {
  name     = "${var.project_name}-bedrock-${var.environment}"
  role_arn = aws_iam_role.bedrock_execution_role.arn
  knowledge_base_configuration {
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"

      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          embedding_data_type = "FLOAT32"
        }
      }
    }
    type = "VECTOR"
  }
  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.forex_kb.arn
      vector_index_name = "bedrock-knowledge-base-default-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }
  depends_on = [
    aws_opensearchserverless_collection.forex_kb,
    aws_iam_role_policy_attachment.bedrock_policy_attachment
  ]
}
resource "aws_bedrockagent_data_source" "example" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.bedrock_kb.id
  name              = "${aws_bedrockagent_knowledge_base.bedrock_kb.name}-data-source"
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = var.s3_file_storage
    }
  }
  data_deletion_policy = "RETAIN"
}

resource "aws_opensearchserverless_security_policy" "forex_kb_encryption" {
  name = var.kb_oss_collection_name
  type = "encryption"
  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/${var.kb_oss_collection_name}"
        ]
        ResourceType = "collection"
      }
    ],
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "forex_kb_network" {
  name = var.kb_oss_collection_name
  type = "network"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${var.kb_oss_collection_name}"
          ]
        },
        {
          ResourceType = "dashboard"
          Resource = [
            "collection/${var.kb_oss_collection_name}"
          ]
        }
      ]
      AllowFromPublic = true
    }
  ])
}
resource "aws_opensearchserverless_access_policy" "forex_kb" {
  name = var.kb_oss_collection_name
  type = "data"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index"
          Resource = [
            "index/${var.kb_oss_collection_name}/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:UpdateIndex",
            "aoss:WriteDocument"
          ]
        },
        {
          ResourceType = "collection"
          Resource = [
            "collection/${var.kb_oss_collection_name}"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DescribeCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DeleteCollectionItems"
          ]
        }
      ],
      Principal = [
        aws_iam_role.bedrock_execution_role.arn,
        data.aws_caller_identity.this.arn
      ]
    }
  ])
}