terraform {
  required_providers {
    aws     = { source = "hashicorp/aws" }
    archive = { source = "hashicorp/archive" }
  }
}

# --- Package the Lambda source ---
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/build/ingestion.zip"
}

# --- Documents bucket (admin uploads policies/FAQs here) ---
resource "aws_s3_bucket" "docs" {
  bucket = "${var.name_prefix}-docs"
  tags   = { Name = "${var.name_prefix}-docs" }
}

resource "aws_s3_bucket_public_access_block" "docs" {
  bucket                  = aws_s3_bucket.docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- Queue + dead-letter queue ---
resource "aws_sqs_queue" "dlq" {
  name = "${var.name_prefix}-ingest-dlq"
}

resource "aws_sqs_queue" "main" {
  name                       = "${var.name_prefix}-ingest"
  visibility_timeout_seconds = var.lambda_timeout * 6
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

# Allow S3 to publish ObjectCreated events to the queue.
data "aws_iam_policy_document" "queue" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.main.arn]
    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_s3_bucket.docs.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "main" {
  queue_url = aws_sqs_queue.main.id
  policy    = data.aws_iam_policy_document.queue.json
}

resource "aws_s3_bucket_notification" "docs" {
  bucket = aws_s3_bucket.docs.id
  queue {
    queue_arn = aws_sqs_queue.main.arn
    events    = ["s3:ObjectCreated:*"]
  }
  depends_on = [aws_sqs_queue_policy.main]
}

# --- Lambda networking (reaches RDS in private subnets) ---
resource "aws_security_group" "lambda" {
  name        = "${var.name_prefix}-ingest-lambda-sg"
  description = "Ingestion Lambda egress"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name_prefix}-ingest-lambda-sg" }
}

# --- IAM ---
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.name_prefix}-ingest-lambda"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

data "aws_iam_policy_document" "permissions" {
  statement {
    sid       = "ReadDocs"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.docs.arn}/*"]
  }
  statement {
    sid       = "ReadSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.db_url_secret_arn]
  }
  statement {
    sid       = "InvokeBedrock"
    actions   = ["bedrock:InvokeModel"]
    resources = ["*"]
  }
  statement {
    sid       = "ConsumeQueue"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.main.arn]
  }
}

resource "aws_iam_role_policy" "permissions" {
  name   = "ingestion-permissions"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.permissions.json
}

# --- Function ---
resource "aws_lambda_function" "ingest" {
  function_name    = "${var.name_prefix}-ingest"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  timeout          = var.lambda_timeout
  memory_size      = 512
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  layers           = var.layers # must provide psycopg + pgvector

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_SECRET_ARN = var.db_url_secret_arn
    }
  }
}

resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn = aws_sqs_queue.main.arn
  function_name    = aws_lambda_function.ingest.arn
  batch_size       = 1
}
