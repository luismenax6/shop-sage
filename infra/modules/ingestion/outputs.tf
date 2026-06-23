output "docs_bucket" {
  description = "Upload documents here to trigger ingestion."
  value       = aws_s3_bucket.docs.bucket
}

output "lambda_security_group_id" {
  value = aws_security_group.lambda.id
}

output "queue_url" {
  value = aws_sqs_queue.main.id
}

output "lambda_function_name" {
  value = aws_lambda_function.ingest.function_name
}
