# Infrastructure (Terraform)

AWS infrastructure for shop-sage, as reusable modules wired together by a `dev`
environment.

## Layout

```
infra/
├── modules/
│   ├── network/   # VPC, public/private subnets, IGW, NAT, route tables
│   ├── alb/       # ALB, security group, target group (health check /health)
│   ├── ecs/       # ECR, cluster, Fargate task + service, IAM roles, logs
│   ├── rds/       # Postgres 16, subnet group, SG, password + DATABASE_URL secret
│   ├── cdn/       # S3 + CloudFront (OAC) for the Angular frontend
│   ├── cognito/   # user pool + SPA client
│   └── ingestion/ # S3 docs -> SQS -> Lambda -> pgvector (event-driven ingestion)
└── envs/dev/      # wires the modules; this is where you run terraform
    └── tests/     # terraform test (mocked providers, no AWS calls)
```

## Architecture

```
            CloudFront (OAC) ── S3            Cognito
                  │  static Angular
   user ──────────┤
                  │  /chat, /cart, /health
            ALB ──── ECS Fargate (backend) ───── RDS Postgres + pgvector
                              │                          ▲
                          Bedrock (Titan + Claude)       │ embeddings
                                                         │
   admin ─ upload ─ S3 (docs) ─ SQS ─ Lambda (chunk + embed)
```

Notable choices:
- **ECS Fargate, not Lambda** — the C extension is compiled in `docker build`.
- **OAC, never OAI** for CloudFront → S3.
- The full `DATABASE_URL` lives in **Secrets Manager** and is injected into the
  task, so the app code needs no change between local and cloud.
- Security groups chain linearly (ALB → ECS → RDS); the ECS SG is created in the
  env (not the ecs module) to avoid an ECS↔RDS dependency cycle.
- IAM uses least privilege: the task role only gets `bedrock:InvokeModel`; the
  execution role only reads the one DB secret. No account IDs or ARNs hardcoded.
- **Event-driven ingestion** runs on Lambda (no C extension needed there): an S3
  `ObjectCreated` event goes to SQS, and the Lambda chunks + embeds into pgvector,
  with a DLQ for failures. The Lambda needs a psycopg + pgvector layer
  (`module.ingestion` `layers` variable).

## Usage

```bash
cd infra/envs/dev
terraform init
terraform plan      # review
terraform apply     # provisions ~55 real AWS resources (costs money)
```

State is local for now; for a team, switch to the S3 backend stub in
`providers.tf`.

## Deploy flow (after apply)

Run from `infra/envs/dev`. `--platform linux/amd64` keeps the image compatible
with Fargate (x86_64) even when built on Apple Silicon. See the root
[README](../README.md#deploy-to-aws) for a copy-paste version that captures the
`terraform output` values into variables.

```bash
# 1. Backend image -> ECR (backend is three levels up from envs/dev)
aws ecr get-login-password | docker login --username AWS --password-stdin <ecr_url>
docker build --platform linux/amd64 -t <ecr_url>:latest ../../../backend
docker push <ecr_url>:latest
aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment

# 2. Frontend -> S3 + CloudFront
( cd ../../../frontend && npm install && npm run build )
aws s3 sync ../../../frontend/dist/frontend/browser s3://<frontend_bucket> --delete
aws cloudfront create-invalidation --distribution-id <id> --paths '/*'
```

(`<...>` values come from `terraform output`.)

## Tests

```bash
cd infra/envs/dev
terraform test     # plan-time assertions with mock_provider — no credentials needed
```
