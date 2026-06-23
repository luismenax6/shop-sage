terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # State is local for now. For a team, switch to an S3 backend + DynamoDB lock.
  # backend "s3" {}
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "shop-sage"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}
