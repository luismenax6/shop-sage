output "db_address" {
  value = aws_db_instance.this.address
}

output "db_url_secret_arn" {
  value       = aws_secretsmanager_secret.db_url.arn
  description = "Secrets Manager ARN holding the full DATABASE_URL."
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}
