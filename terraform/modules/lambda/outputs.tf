output "incident_processor_arn" {
  value = aws_lambda_function.incident_processor.arn
}

output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}
