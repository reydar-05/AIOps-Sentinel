output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "sns_topic_arn" {
  description = "SNS alerts topic ARN"
  value       = aws_sns_topic.aiops_alerts.arn
}

output "dynamodb_table_name" {
  description = "DynamoDB incidents table name"
  value       = aws_dynamodb_table.incidents.name
}

output "s3_log_bucket" {
  description = "S3 log archive bucket name"
  value       = aws_s3_bucket.log_archive.bucket
}

output "lambda_function_arn" {
  description = "Incident processor Lambda ARN"
  value       = module.lambda.incident_processor_arn
}

output "autoscaling_group_name" {
  description = "Auto Scaling Group name"
  value       = module.ec2.autoscaling_group_name
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS"
  value       = module.ec2.alb_dns_name
}
