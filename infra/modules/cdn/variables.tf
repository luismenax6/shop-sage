variable "name_prefix" {
  type = string
}

variable "alb_domain_name" {
  type        = string
  description = "ALB DNS name; CloudFront routes /chat and /cart to it."
}
