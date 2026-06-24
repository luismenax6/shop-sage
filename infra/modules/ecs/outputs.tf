output "ecr_repository_url" {
  value = aws_ecr_repository.this.repository_url
}

output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "service_name" {
  value = aws_ecs_service.this.name
}

output "task_definition_arn" {
  description = "For one-off tasks (e.g. the DB bootstrap)."
  value       = aws_ecs_task_definition.this.arn
}
