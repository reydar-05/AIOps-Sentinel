variable "environment" { type = string }
variable "aws_region" { type = string }
variable "aws_account_id" { type = string }
variable "sns_topic_arn" { type = string }
variable "lambda_execution_role_arn" { type = string }
variable "dynamodb_table_name" { type = string }
variable "s3_log_bucket" { type = string }

variable "groq_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "groq_max_tokens" {
  type    = string
  default = "2048"
}

variable "discord_webhook_url" {
  type      = string
  default   = ""
  sensitive = true
}

variable "discord_review_webhook_url" {
  description = "Optional Discord webhook for LOW-confidence alerts that need human review"
  type        = string
  default     = ""
  sensitive   = true
}

variable "groq_daily_token_limit" {
  description = "Soft daily token ceiling for Groq calls; logs WARN above this"
  type        = string
  default     = "100000"
}
