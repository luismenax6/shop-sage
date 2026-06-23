variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnets the ALB lives in."
}

variable "container_port" {
  type        = number
  default     = 5000
  description = "Port the backend container listens on."
}

variable "health_check_path" {
  type    = string
  default = "/health"
}
