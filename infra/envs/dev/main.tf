locals {
  name_prefix    = "shopsage-${terraform.workspace == "default" ? "dev" : terraform.workspace}"
  container_port = 5000
}

module "network" {
  source               = "../../modules/network"
  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  azs                  = var.azs
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

module "alb" {
  source            = "../../modules/alb"
  name_prefix       = local.name_prefix
  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  container_port    = local.container_port
}

# ECS service security group lives here (not in the ecs module) so RDS and ECS
# don't form a dependency cycle. Chain: alb_sg -> ecs_sg -> rds_sg.
resource "aws_security_group" "ecs_service" {
  name        = "${local.name_prefix}-ecs-sg"
  description = "Allow traffic from the ALB to the backend container"
  vpc_id      = module.network.vpc_id

  ingress {
    description     = "From the ALB"
    from_port       = local.container_port
    to_port         = local.container_port
    protocol        = "tcp"
    security_groups = [module.alb.alb_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-ecs-sg" }
}

module "rds" {
  source                = "../../modules/rds"
  name_prefix           = local.name_prefix
  vpc_id                = module.network.vpc_id
  private_subnet_ids    = module.network.private_subnet_ids
  ecs_security_group_id = aws_security_group.ecs_service.id
}

module "ecs" {
  source                    = "../../modules/ecs"
  name_prefix               = local.name_prefix
  vpc_id                    = module.network.vpc_id
  private_subnet_ids        = module.network.private_subnet_ids
  service_security_group_id = aws_security_group.ecs_service.id
  target_group_arn          = module.alb.target_group_arn
  db_url_secret_arn         = module.rds.db_url_secret_arn
  container_port            = local.container_port
  image_tag                 = var.image_tag
}

# Event-driven ingestion: docs land in S3 -> SQS -> Lambda embeds into pgvector.
module "ingestion" {
  source             = "../../modules/ingestion"
  name_prefix        = local.name_prefix
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  db_url_secret_arn  = module.rds.db_url_secret_arn
}

# Let the ingestion Lambda reach RDS (added here to keep the rds module unaware
# of the ingestion module).
resource "aws_security_group_rule" "rds_from_ingest_lambda" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = module.rds.rds_security_group_id
  source_security_group_id = module.ingestion.lambda_security_group_id
}

module "cdn" {
  source      = "../../modules/cdn"
  name_prefix = local.name_prefix
}

module "cognito" {
  source        = "../../modules/cognito"
  name_prefix   = local.name_prefix
  callback_urls = var.cognito_callback_urls
}
