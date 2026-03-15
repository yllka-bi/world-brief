resource "aws_codebuild_project" "infrastructure" {
  name          = var.build_name
  description   = var.project_description
  build_timeout = "120"
  service_role  = aws_iam_role.project_role.arn


  artifacts {
    type = "CODEPIPELINE"
  }

  cache {
    type = "NO_CACHE"
  }

  environment {
    compute_type                = var.codebuild_compute_size
    image                       = var.codebuild_compute_image
    type                        = var.codebuild_compute_type
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "ENVIRONMENT"
      value = var.environment
    }

    environment_variable {
      name  = "AWSREGION"
      value = var.aws_region
    }
    environment_variable {
      name  = "PROJECT_NAME"
      value = var.project_name
    }

    # environment_variable {
    #   name  = "AWS_ACCESS_KEY_ID"
    #   value = var.aws_access_key_id
    # }

    environment_variable {
      name  = "AWSACCOUNT_ID"
      value = var.aws_account_id
    }

    environment_variable {
      name  = "TERRAFORM_STATE_BUCKET"
      value = var.terraform_state_bucket
    }
  }

  logs_config {
    cloudwatch_logs {
      group_name  = "log-group"
      stream_name = "log-stream"
    }

    s3_logs {
      status   = "ENABLED"
      location = "${aws_s3_bucket.cicd_storage_bucket.id}/build-log"
    }
  }

  source {
    buildspec = var.buildspec_file_path
    type      = "CODEPIPELINE"
  }

  source_version = var.codebuild_source_version

}
