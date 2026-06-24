terraform {
  required_providers {
    aws    = { source = "hashicorp/aws" }
    random = { source = "hashicorp/random" }
  }
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.name_prefix}-db-subnets"
  subnet_ids = var.private_subnet_ids
  tags       = { Name = "${var.name_prefix}-db-subnets" }
}

resource "aws_security_group" "rds" {
  name        = "${var.name_prefix}-rds-sg"
  description = "Allow Postgres from the ECS service only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Postgres from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ecs_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name_prefix}-rds-sg" }
}

resource "random_password" "db" {
  length = 24
  # URL-safe special chars so the password embeds cleanly in DATABASE_URL
  override_special = "-_.~"
}

resource "aws_db_instance" "this" {
  identifier             = "${var.name_prefix}-pg"
  engine                 = "postgres"
  engine_version         = var.engine_version
  instance_class         = var.instance_class
  allocated_storage      = var.allocated_storage
  storage_encrypted      = true
  db_name                = var.db_name
  username               = var.db_username
  password               = random_password.db.result
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  multi_az               = false
  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false
  apply_immediately      = true

  tags = { Name = "${var.name_prefix}-pg" }
}

# Full connection string in Secrets Manager; the ECS task injects it as
# DATABASE_URL, so the app code stays unchanged. pgvector ships with RDS
# Postgres 16 and is enabled at the SQL level (CREATE EXTENSION vector).
resource "aws_secretsmanager_secret" "db_url" {
  name        = "${var.name_prefix}-database-url"
  description = "DATABASE_URL for the shop-sage backend"
  # Delete immediately on destroy (dev/demo) so re-applying doesn't hit a
  # name still scheduled for deletion.
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db_url" {
  secret_id = aws_secretsmanager_secret.db_url.id
  secret_string = format(
    "postgresql://%s:%s@%s:5432/%s",
    var.db_username,
    random_password.db.result,
    aws_db_instance.this.address,
    var.db_name,
  )
}
