variable "environment" { type = string }
variable "aws_region" { type = string }
variable "aws_account_id" { type = string }
variable "sns_topic_arn" { type = string }
variable "lambda_execution_role_arn" { type = string }
variable "bedrock_model_id" { type = string }
variable "dynamodb_table_name" { type = string }
variable "s3_log_bucket" { type = string }
variable "slack_secret_name" { type = string }
variable "groq_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "bedrock_max_tokens" {
  type    = string
  default = "2048"
}
