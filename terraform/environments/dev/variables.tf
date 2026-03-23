variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "ami_id" {
  description = "AMI ID for EC2 instances (Amazon Linux 2023)"
  type        = string
  # Latest Amazon Linux 2023 in ap-south-1
  default     = "ami-0f58b397bc5c1f2e8"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "asg_min_size" {
  description = "Minimum number of EC2 instances in ASG"
  type        = number
  default     = 1
}

variable "asg_max_size" {
  description = "Maximum number of EC2 instances in ASG"
  type        = number
  default     = 3
}

variable "asg_desired_capacity" {
  description = "Desired number of EC2 instances in ASG"
  type        = number
  default     = 2
}

variable "cpu_alarm_threshold" {
  description = "CPU utilization % to trigger alarm"
  type        = number
  default     = 80
}

variable "alert_email" {
  description = "Email address for SNS alert notifications"
  type        = string
  default     = ""
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for incidents"
  type        = string
  default     = "aiops-incidents"
}

variable "s3_log_bucket" {
  description = "S3 bucket name for log archiving"
  type        = string
  default     = "aiops-log-archive"
}

variable "slack_secret_name" {
  description = "Secrets Manager secret name for Slack webhook"
  type        = string
  default     = "aiops/slack/webhook"
}

variable "groq_api_key" {
  description = "OpenRouter/Groq API key for fallback AI analysis"
  type        = string
  sensitive   = true
  default     = ""
}
