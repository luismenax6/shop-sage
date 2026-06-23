variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "db_url_secret_arn" {
  type        = string
  description = "Secrets Manager ARN with DATABASE_URL (the Lambda writes embeddings to pgvector)."
}

variable "layers" {
  type        = list(string)
  default     = []
  description = "Lambda layer ARNs providing psycopg + pgvector at runtime."
}

variable "lambda_timeout" {
  type    = number
  default = 60
}
