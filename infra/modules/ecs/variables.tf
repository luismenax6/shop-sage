variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "service_security_group_id" {
  type        = string
  description = "Security group attached to the Fargate tasks (created in the env to avoid a cycle with RDS)."
}

variable "target_group_arn" {
  type        = string
  description = "ALB target group the service registers into."
}

variable "db_url_secret_arn" {
  type        = string
  description = "Secrets Manager ARN with DATABASE_URL."
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "container_port" {
  type    = number
  default = 5000
}

variable "task_cpu" {
  type    = number
  default = 512
}

variable "task_memory" {
  type    = number
  default = 1024
}

variable "desired_count" {
  type    = number
  default = 1
}
