resource "aws_codestarconnections_connection" "connection" {
  name          = var.codestar_connection
  provider_type = var.provider_type

}

resource "aws_codepipeline" "infrastructure_pipeline" {

  depends_on = [
    aws_codebuild_project.infrastructure,
    aws_iam_role.project_role
  ]

  name             = var.pipeline_name
  role_arn         = aws_iam_role.project_role.arn
  pipeline_type = "V2"

  artifact_store {
    location = aws_s3_bucket.cicd_storage_bucket.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["SourceOutput"]

      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.connection.arn
        FullRepositoryId = var.repository_path
        BranchName       = var.repository_branch
        DetectChanges    = true
      }
    }
  }

  stage {
    name = "Build"
    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeBuild"
      input_artifacts  = ["SourceOutput"]
      output_artifacts = ["BuildOutput"]
      run_order        = 1
      configuration = {
        ProjectName = aws_codebuild_project.infrastructure.id
      }
    }
  }

  trigger {
    provider_type = "CodeStarSourceConnection"

    git_configuration {
      source_action_name = "Source"

      push {
        # Optional branch filters
        branches {
          includes = ["${var.repository_branch}"] 
        }

        # Optional file path filters (glob patterns)
        file_paths {
          # Only run if ANY changed file matches one of these
          includes = [
            var.trigger_file_paths
          ]
          # Even if include matches, skip if ALL changed files are excluded
          excludes = [
            var.trigger_file_paths_excludes
          ]
        }
      }
    }
  }
}
