# ShopSage 🛒

An AI shopping assistant for e-commerce — a conversational interface that helps
shoppers find the right product, answers support questions grounded in real
policy documents (RAG), and takes actions on their behalf via tool-calling.

> Portfolio project. A focused, mini take on a conversational commerce assistant
> (in the spirit of Capacity.com) — **not** a full e-commerce storefront. The
> core is the chat experience, retrieval-augmented answers, and agent actions.

![ShopSage demo — chat, in-chat product cards, live cart](demo/shopsage-chat.gif)

## Example

> **Shopper:** "A gift for my dad who camps, under $100."
>
> **ShopSage:** recommends real in-stock products from the catalog, answers
> follow-up questions about shipping/returns with citations, and can add an item
> to the cart or escalate to a human — all in one conversation.

---

## Architecture

![ShopSage architecture on AWS](demo/shopsage-architecture.png)

> Diagram generated from code — `python demo/architecture_diagram.py`.

| Layer | Tech |
| --- | --- |
| Frontend | Angular (chat UI, in-chat product cards, mini-cart, citations, markdown) |
| Backend | Flask (Python), app-factory pattern |
| Retrieval acceleration | **C extension** called from Python for cosine similarity |
| LLM & embeddings | AWS Bedrock — Claude (generation) + Amazon Titan Text v2 (embeddings, 1024-dim) |
| Vector + relational store | PostgreSQL 16 + **pgvector** (catalog, orders, tickets, cart, embeddings) |
| Agent actions | Tool-calling: `search_products` / `search_documentation` (read), `add_to_cart` / `create_ticket` (write) |
| Infra | AWS via Terraform — CloudFront + S3, ALB → ECS Fargate, RDS, Cognito, Secrets Manager, CloudWatch, and an event-driven ingestion pipeline (S3 → SQS → Lambda) |

The Flask backend runs on **ECS Fargate** (not Lambda) specifically because the
C extension is compiled during `docker build`.

---

## RAG pipeline

**Ingestion (one-shot)** — `backend/scripts/ingest.py`
```
data/policies/*.md → chunk by section → embed (Titan v2) → store in document_chunks (pgvector)
```

In AWS this runs as an **event-driven pipeline**: documents land in S3, an event
goes to SQS, and a Lambda chunks + embeds them into pgvector (see `infra/`).

**Retrieval (per query)** — `backend/app/rag/retrieval.py`
```
question → embed (Titan v2) → pgvector/HNSW candidate pool → exact cosine re-score in C → guardrail
```

Two-stage retrieval: pgvector + an HNSW index does fast approximate
nearest-neighbour search to gather a candidate pool, then the C extension
recomputes exact cosine similarity to drive the final ranking. An
**anti-hallucination guardrail** returns "no information available" when no chunk
clears the similarity threshold, instead of letting the model invent an answer.
Each chunk keeps its source document and section, so support answers can be
**cited**.

---

## The agent

A single Bedrock Converse tool-calling loop (`backend/app/agent/`) routes every
message. Claude decides which tool to call:

| Tool | Type | Notes |
| --- | --- | --- |
| `search_products` | read | Filter catalog by category, price, stock, keywords |
| `search_documentation` | read | RAG lookup over policy docs, returns cited chunks |
| `add_to_cart` | write | Confirmation-gated + idempotent (UPSERT) |
| `create_ticket` | write | Confirmation-gated + idempotent (reuses open ticket) |

Write safety:
- **Confirmation gate** — write tools never execute until the request carries
  `confirm: true`; the agent asks the shopper first (enforced in both the system
  prompt and the orchestrator).
- **Idempotency** — retrying a write never duplicates (DB `UNIQUE` constraints).
- **Server-supplied identity** — `user_id` is injected by the backend, never
  chosen by the model.

### `POST /chat`

```bash
curl -X POST localhost:5001/chat -H 'Content-Type: application/json' \
  -d '{"message": "gift for my dad who camps, under 100"}'
```
Returns `{ answer, citations, products, cart, tool_calls, history }`. The
`history` round-trips so a multi-turn exchange (e.g. confirm-before-write) can
continue.

`POST /cart/add` and `GET /cart` handle deterministic cart actions (a product
card's "Add" button) directly, bypassing the LLM — natural language goes through
the agent, button clicks do not. Both reuse the same idempotent cart logic.

## Frontend

Angular 21 (standalone components + signals) in `frontend/`. A single chat view:

- chat window with user/assistant bubbles and markdown rendering
- **in-chat product cards** (image, price, stock, Add button) built from the
  structured `products` the backend returns alongside the prose
- **live mini-cart** kept in sync from `/chat` and `/cart/add` responses
- **citation chips** under support answers showing the source document/section

A dev proxy (`proxy.conf.json`) forwards `/chat`, `/cart`, and `/health` to the
Flask backend on `:5001`.

```bash
cd frontend && npm install && npm start   # http://localhost:4200
```

## C extension benchmark

Cosine similarity is the hot loop of retrieval. It's implemented as a CPython
extension (`backend/csim/cosine.c`) that operates on raw `double` buffers via the
buffer protocol, so the loop runs entirely in native code.

Scoring **1 query vs 20,000 vectors (dim 1024)**:

| Implementation | Time | vs pure Python |
| --- | --- | --- |
| Pure Python | 1974.8 ms | 1× |
| **C extension** | **30.4 ms** | **64.9× faster** |
| NumPy (per vector) | 65.7 ms | 30× |
| NumPy (vectorized) | 43.7 ms | 45× |

All implementations agree on the result (correctness asserted in the benchmark).
Reproduce with `python scripts/benchmark.py`.

---

## Tests

```bash
cd backend && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                     # needs the dev DB running (docker compose up) and seeded
```

18 tests covering the C cosine extension (correctness + error cases), markdown
chunking, catalog search filters, write-tool idempotency (cart + tickets), and
the retrieval guardrail threshold (Bedrock mocked, no network call).

## Repository structure

```
shop-sage/
├── docker-compose.yml          # local Postgres + pgvector
├── data/                       # synthetic dataset (gifts / Father's Day theme)
│   ├── products.json           #   30 products · orders.json (12 orders)
│   └── policies/               #   7 policy/FAQ documents (RAG source)
├── backend/                    # Flask
│   ├── app/
│   │   ├── api/                #   health, chat, cart endpoints
│   │   ├── agent/              #   tools + Bedrock tool-calling orchestrator
│   │   ├── bedrock/            #   Titan embeddings + Claude generation clients
│   │   └── rag/                #   two-stage retrieval + guardrail
│   ├── csim/                   #   C extension (cosine similarity)
│   ├── db/schema.sql           #   tables + pgvector + HNSW index
│   ├── scripts/                #   seed_data.py, ingest.py, benchmark.py
│   ├── tests/                  #   pytest suite (18 tests)
│   └── Dockerfile              #   compiles the C extension (why Fargate)
├── frontend/                   # Angular: chat UI, product cards, mini-cart
├── infra/                      # Terraform: modules + dev env (validated + tested)
│   ├── modules/                #   network, alb, ecs, rds, cdn, cognito, ingestion
│   └── envs/dev/
└── demo/                       # AWS architecture diagram + recorded demo (Playwright)
```

---

## Run it locally (end to end)

Prerequisites: Docker, Node 20+, Python 3.11+, a C compiler, `psql`, and AWS
credentials with Bedrock model access (Claude + Titan embeddings) in `us-east-1`.

### 1. One-time setup

```bash
# Database
docker compose up -d                 # Postgres + pgvector

# Backend: env, dependencies, C extension
cd backend
cp .env.example .env                 # local DATABASE_URL is preconfigured
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install ./csim                   # builds & installs the C extension

# Schema + synthetic data (export DATABASE_URL so psql can read it)
export DATABASE_URL="postgresql://shopsage:shopsage_local_dev@localhost:5432/shopsage"
psql "$DATABASE_URL" -f db/schema.sql
python scripts/seed_data.py          # products + orders
python scripts/ingest.py             # embeds policy docs into pgvector (needs AWS Bedrock)

# Frontend dependencies
cd ../frontend && npm install
```

### 2. Start the app

Two terminals (the database keeps running in the background from setup):

```bash
# Terminal 1 — backend (from backend/, with the venv active)
flask --app wsgi run --port 5001

# Terminal 2 — frontend (from frontend/)
npm start                            # ng serve on :4200, proxies /chat + /cart to :5001
```

Then open **http://localhost:4200** and try:

- *"a gift for my dad who camps, under $100"* → product cards; click **Add to cart**
- *"can I return a Father's Day gift after 45 days?"* → answer with citations
- *"do you have a store in Madrid?"* → guardrail (says it doesn't know, no hallucination)

Quick backend check on its own: `curl localhost:5001/health` → `{"status":"ok","db":"up"}`.

> Only `scripts/ingest.py` and the chat itself need AWS Bedrock. The schema, seed,
> `/health`, and the test suite all run without AWS.

---

## Deploy to AWS

All infrastructure lives in Terraform under `infra/` — VPC, ALB → ECS Fargate,
RDS + pgvector, CloudFront + S3, Cognito, and the event-driven ingestion pipeline
(S3 → SQS → Lambda). It's formatted, validated, and covered by `terraform test`;
`apply` provisions ~55 resources. Module breakdown: [`infra/README.md`](infra/README.md).

```bash
cd infra/envs/dev
terraform init
terraform apply                      # provisions the stack (~55 resources)

# Backend image -> ECR, then roll the ECS service
ECR=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$ECR"
docker build -t "$ECR:latest" ../../backend && docker push "$ECR:latest"
aws ecs update-service --cluster "$(terraform output -raw ecs_cluster_name)" \
  --service "$(terraform output -raw ecs_service_name)" --force-new-deployment

# Frontend -> S3 + CloudFront
( cd ../../frontend && npm run build )
aws s3 sync ../../frontend/dist/frontend/browser \
  "s3://$(terraform output -raw frontend_bucket)" --delete
aws cloudfront create-invalidation \
  --distribution-id "$(terraform output -raw cloudfront_distribution_id)" --paths '/*'
```

The Lambda needs a psycopg + pgvector layer at deploy time (`module.ingestion`
`layers` variable). After ingestion is wired, upload policy docs to the `*-docs`
S3 bucket to trigger embedding.

> This runs real, billable services (NAT, RDS, ALB, Fargate, CloudFront). Run
> `terraform destroy` after a demo to tear everything down.
