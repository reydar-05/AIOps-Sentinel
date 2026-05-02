# ── Placeholder Lambda handler (replaced in Phase 7 deployment) ───
data "archive_file" "placeholder" {
  type        = "zip"
  output_path = "${path.module}/placeholder.zip"

  source {
    content  = "def lambda_handler(event, context):\n    return {'statusCode': 200, 'body': 'AIOps Sentinel placeholder'}\n"
    filename = "handler.py"
  }
}

# ── Lambda: Incident Processor ────────────────────────────────────
resource "aws_lambda_function" "incident_processor" {
  function_name    = "aiops-incident-processor-${var.environment}"
  role             = var.lambda_execution_role_arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  timeout          = 300
  memory_size      = 512
  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  environment {
    variables = {
      ENVIRONMENT         = var.environment
      AWS_ACCOUNT_ID_VAR  = var.aws_account_id
      GROQ_MAX_TOKENS     = var.groq_max_tokens
      DYNAMODB_TABLE_NAME        = "${var.dynamodb_table_name}-${var.environment}"
      S3_LOG_BUCKET              = "${var.s3_log_bucket}-${var.environment}"
      SNS_TOPIC_ARN              = var.sns_topic_arn
      GROQ_API_KEY               = var.groq_api_key
      GROQ_DAILY_TOKEN_LIMIT     = var.groq_daily_token_limit
      DISCORD_WEBHOOK_URL        = var.discord_webhook_url
      DISCORD_REVIEW_WEBHOOK_URL = var.discord_review_webhook_url
      LOG_LEVEL                  = "INFO"
    }
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.dlq.arn
  }

  tracing_config {
    mode = "Active"  # X-Ray tracing
  }

  tags = {
    Name = "aiops-incident-processor-${var.environment}"
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }

  depends_on = [data.archive_file.placeholder]
}

# ── Dead Letter Queue ─────────────────────────────────────────────
resource "aws_sqs_queue" "dlq" {
  name                      = "aiops-lambda-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name = "aiops-lambda-dlq-${var.environment}"
  }
}

# ── Lambda Permission: Allow SNS to invoke ────────────────────────
resource "aws_lambda_permission" "allow_sns" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.incident_processor.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = var.sns_topic_arn
}

# ── SNS → Lambda subscription ─────────────────────────────────────
resource "aws_sns_topic_subscription" "lambda_trigger" {
  topic_arn = var.sns_topic_arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.incident_processor.arn
}

# ── CloudWatch Log Group for Lambda ──────────────────────────────
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/aiops-incident-processor-${var.environment}"
  retention_in_days = 30
}
