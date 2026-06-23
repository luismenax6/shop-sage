variable "name_prefix" {
  type = string
}

variable "callback_urls" {
  type        = list(string)
  description = "Allowed OAuth callback URLs for the SPA."
  default     = ["http://localhost:4200"]
}
