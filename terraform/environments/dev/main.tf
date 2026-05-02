terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }

  backend "s3" {
    bucket = "aiops-terraform-state-652197206400"
    key    = "dev/terraform.tfstate"
    region = "ap-south-1"
  }
}

data "aws_caller_identity" "current" {}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AIOps-Sentinel"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "aiops-team"
    }
  }
}

# ── Networking ────────────────────────────────────────────────────
module "networking" {
  source      = "../../modules/networking"
  environment = var.environment
  aws_region  = var.aws_region
}

# ── IAM ───────────────────────────────────────────────────────────
module "iam" {
  source         = "../../modules/iam"
  environment    = var.environment
  aws_account_id = data.aws_caller_identity.current.account_id
  aws_region     = var.aws_region
}

# ── SNS ───────────────────────────────────────────────────────────
resource "aws_sns_topic" "aiops_alerts" {
  name = "aiops-alerts-${var.environment}"
}

resource "aws_sns_topic_subscription" "email_alert" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.aiops_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ── EC2 + Auto Scaling ────────────────────────────────────────────
module "ec2" {
  source                    = "../../modules/ec2"
  environment               = var.environment
  vpc_id                    = module.networking.vpc_id
  public_subnet_ids         = module.networking.public_subnet_ids
  private_subnet_ids        = module.networking.private_subnet_ids
  ec2_instance_profile_name = module.iam.ec2_instance_profile_name
  ami_id                    = var.ami_id
  instance_type             = var.instance_type
  min_size                  = var.asg_min_size
  max_size                  = var.asg_max_size
  desired_capacity          = var.asg_desired_capacity
  ec2_security_group_id     = module.networking.ec2_security_group_id
  alb_security_group_id     = module.networking.alb_security_group_id
}

# ── CloudWatch Alarms ─────────────────────────────────────────────
module "alarms" {
  source                = "../../modules/alarms"
  environment           = var.environment
  sns_topic_arn         = aws_sns_topic.aiops_alerts.arn
  autoscaling_group_name = module.ec2.autoscaling_group_name
  cpu_alarm_threshold   = var.cpu_alarm_threshold
}

# ── Lambda ────────────────────────────────────────────────────────
module "lambda" {
  source                    = "../../modules/lambda"
  environment               = var.environment
  aws_region                = var.aws_region
  aws_account_id            = data.aws_caller_identity.current.account_id
  sns_topic_arn             = aws_sns_topic.aiops_alerts.arn
  lambda_execution_role_arn = module.iam.lambda_execution_role_arn
  dynamodb_table_name       = var.dynamodb_table_name
  s3_log_bucket             = var.s3_log_bucket
  groq_api_key              = var.groq_api_key
  groq_max_tokens           = "2048"
  groq_daily_token_limit    = var.groq_daily_token_limit
  discord_webhook_url       = var.discord_webhook_url
  discord_review_webhook_url = var.discord_review_webhook_url
}

# ── DynamoDB ──────────────────────────────────────────────────────
resource "aws_dynamodb_table" "incidents" {
  name         = "${var.dynamodb_table_name}-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "incident_id"
  range_key    = "timestamp"

  attribute {
    name = "incident_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "aiops-incidents-${var.environment}"
  }
}

# ── S3 Log Archive ────────────────────────────────────────────────
resource "aws_s3_bucket" "log_archive" {
  bucket = "${var.s3_log_bucket}-${var.environment}"
}

resource "aws_s3_bucket_lifecycle_configuration" "log_archive_lifecycle" {
  bucket = aws_s3_bucket.log_archive.id

  rule {
    id     = "archive-old-logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "log_archive_sse" {
  bucket = aws_s3_bucket.log_archive.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "log_archive_block" {
  bucket                  = aws_s3_bucket.log_archive.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── EventBridge Rules ─────────────────────────────────────────────
resource "aws_cloudwatch_event_rule" "ec2_state_change" {
  name        = "aiops-ec2-state-change-${var.environment}"
  description = "Capture EC2 instance state changes"

  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["EC2 Instance State-change Notification"]
    detail = {
      state = ["stopped", "terminated", "stopping"]
    }
  })
}

resource "aws_cloudwatch_event_target" "ec2_state_to_sns" {
  rule      = aws_cloudwatch_event_rule.ec2_state_change.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.aiops_alerts.arn
}

resource "aws_sns_topic_policy" "allow_eventbridge" {
  arn = aws_sns_topic.aiops_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "events.amazonaws.com" }
        Action    = "SNS:Publish"
        Resource  = aws_sns_topic.aiops_alerts.arn
      }
    ]
  })
}

