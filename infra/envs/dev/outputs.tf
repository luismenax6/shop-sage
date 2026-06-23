output "alb_dns_name" {
  description = "Public URL of the backend (behind the ALB)."
  value       = module.alb.alb_dns_name
}

output "cloudfront_domain_name" {
  description = "Public URL of the frontend."
  value       = module.cdn.cloudfront_domain_name
}

output "frontend_bucket" {
  value = module.cdn.bucket_name
}

output "ecr_repository_url" {
  description = "Push the backend image here."
  value       = module.ecs.ecr_repository_url
}

output "ecs_cluster_name" {
  value = module.ecs.cluster_name
}

output "ecs_service_name" {
  value = module.ecs.service_name
}

output "ingestion_docs_bucket" {
  description = "Upload policy/FAQ documents here to trigger ingestion."
  value       = module.ingestion.docs_bucket
}

output "cognito_user_pool_id" {
  value = module.cognito.user_pool_id
}

output "cognito_user_pool_client_id" {
  value = module.cognito.user_pool_client_id
}
