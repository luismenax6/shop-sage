variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "ecs_security_group_id" {
  type        = string
  description = "Security group of the ECS service allowed to reach the DB."
}

variable "db_name" {
  type    = string
  default = "shopsage"
}

variable "db_username" {
  type    = string
  default = "shopsage"
}

variable "engine_version" {
  type    = string
  default = "16.10" # RDS deprecates minor versions; bump to an available one
}

variable "instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "allocated_storage" {
  type    = number
  default = 20
}
