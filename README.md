# ShopSage 🛒

An AI shopping assistant for e-commerce — a conversational interface that helps
shoppers find the right product, answers support questions grounded in real
policy documents (RAG), and takes actions on their behalf via tool-calling.

> Portfolio project. A focused, mini take on a conversational commerce assistant
> (in the spirit of Capacity.com) — **not** a full e-commerce storefront. The
> core is the chat experience, retrieval-augmented answers, and agent actions.

## Example

> **Shopper:** "A gift for my dad who camps, under $100."
>
> **ShopSage:** recommends real in-stock products from the catalog, answers
> follow-up questions about shipping/returns with citations, and can add an item
> to the cart or escalate to a human — all in one conversation.

---

## Architecture

| Layer | Tech |
| --- | --- |
| Frontend | Angular (chat UI with streaming, in-chat product cards, mini-cart, citations) |
| Backend | Flask (Python), app-factory pattern |
| Retrieval acceleration | **C extension** called from Python for cosine similarity |
| LLM & embeddings | AWS Bedrock — Claude (generation) + Amazon Titan Text v2 (embeddings, 1024-dim) |
| Vector + relational store | PostgreSQL 16 + **pgvector** (catalog, orders, tickets, cart, embeddings) |
| Agent actions | Tool-calling: `search_products` (read), `add_to_cart` (write), `create_ticket` (write) |
| Infra (target) | AWS via Terraform — CloudFront + S3, ALB → ECS Fargate, RDS, Cognito, Secrets Manager, CloudWatch; CI/CD with GitHub Actions |

The Flask backend runs on **ECS Fargate** (not Lambda) specifically because the
C extension is compiled during `docker build`.

---

## RAG pipeline

**Ingestion (one-shot)** — `backend/scripts/ingest.py`
```
data/policies/*.md → chunk by section → embed (Titan v2) → store in document_chunks (pgvector)
```

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
│   ├── products.json           #   30 products across 6 categories
│   ├── orders.json             #   12 sample orders
│   └── policies/               #   7 policy/FAQ documents (RAG source)
├── backend/                    # Flask
│   ├── app/
│   │   ├── __init__.py         #   create_app() app factory
│   │   ├── api/health.py       #   /health (verifies DB connectivity)
│   │   ├── bedrock/embeddings.py  # shared Titan embedding client
│   │   └── rag/retrieval.py    #   two-stage retrieval + guardrail
│   ├── csim/                   # C extension (cosine similarity)
│   │   ├── cosine.c
│   │   └── setup.py
│   ├── db/schema.sql           # tables + pgvector + HNSW index
│   └── scripts/                # seed_data.py, ingest.py, benchmark.py
├── frontend/                   # Angular: chat UI, product cards, mini-cart
│   └── src/app/                #   app (chat), chat/cart services, markdown pipe
└── infra/                      # Terraform (planned)
```

---

## Local setup

Prerequisites: Docker, Python 3.11+, a C compiler, AWS credentials with Bedrock
model access (Claude + Titan embeddings) in `us-east-1`, and `psql`.

```bash
# 1. Start Postgres + pgvector
docker compose up -d

# 2. Backend environment
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Build & install the C extension
pip install ./csim

# 4. Create the schema and load synthetic data
psql "$DATABASE_URL" -f db/schema.sql
python scripts/seed_data.py        # products + orders
python scripts/ingest.py           # embeds policy docs into pgvector

# 5. Run the backend
flask --app wsgi run --port 5001
curl localhost:5001/health         # {"status":"ok","db":"up"}
```

`DATABASE_URL` (local default):
`postgresql://shopsage:shopsage_local_dev@localhost:5432/shopsage`

---

## Status

- [x] **Day 1** — Monorepo, Postgres + pgvector (Docker), Flask app factory + `/health`
- [x] **Day 2** — SQL schema, synthetic dataset, RAG ingestion (embeddings → pgvector)
- [x] **Day 3** — C cosine extension + benchmark, two-stage retrieval with citations + guardrail
- [x] **Day 4** — Agent: RAG generation (Claude) + tool-calling (search/cart/ticket), `/chat` endpoint
- [x] **Day 5** — Angular chat UI: messages, in-chat product cards, live mini-cart, citations, markdown
- [ ] **Day 6** — AWS infrastructure in Terraform
- [ ] **Day 7** — CI/CD, polish, demo
