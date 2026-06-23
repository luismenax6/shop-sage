variable "name_prefix" {
  type        = string
  description = "Prefix for resource names, e.g. shopsage-dev."
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC."
}

variable "azs" {
  type        = list(string)
  description = "Availability zones to spread subnets across."
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "CIDRs for the public subnets (one per AZ)."
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "CIDRs for the private subnets (one per AZ)."
}
