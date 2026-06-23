# Plan-time tests with mocked providers — no AWS credentials or resources.
# Run from infra/envs/dev:  terraform test

mock_provider "aws" {
  # IAM policy documents must return valid JSON for aws_iam_role validation.
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }
}
mock_provider "random" {}

run "plan_wires_the_stack" {
  command = plan

  assert {
    condition     = length(module.network.public_subnet_ids) == 2
    error_message = "Expected 2 public subnets (one per AZ)."
  }

  assert {
    condition     = length(module.network.private_subnet_ids) == 2
    error_message = "Expected 2 private subnets (one per AZ)."
  }

  assert {
    condition     = aws_security_group.ecs_service.name == "shopsage-dev-ecs-sg"
    error_message = "Resource names should use the shopsage-dev prefix."
  }
}

run "custom_cidr_blocks" {
  command = plan

  variables {
    vpc_cidr             = "172.16.0.0/16"
    public_subnet_cidrs  = ["172.16.0.0/24", "172.16.1.0/24"]
    private_subnet_cidrs = ["172.16.10.0/24", "172.16.11.0/24"]
  }

  assert {
    condition     = length(module.network.private_subnet_ids) == 2
    error_message = "Subnet count should follow the provided CIDR lists."
  }
}
