-- shop-sage schema
-- Postgres 16 + pgvector. Embeddings = 1024 dims (Amazon Titan Text v2).

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- Catálogo
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    sku         TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    description TEXT NOT NULL,
    image_url   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);
CREATE INDEX IF NOT EXISTS idx_products_price    ON products (price);

-- ---------------------------------------------------------------------------
-- Pedidos
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id            SERIAL PRIMARY KEY,
    order_number  TEXT UNIQUE NOT NULL,
    user_id       TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'processing'
                  CHECK (status IN ('processing', 'shipped', 'delivered', 'cancelled', 'returned')),
    total         NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (total >= 0),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON orders (user_id);

CREATE TABLE IF NOT EXISTS order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products (id),
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items (order_id);

-- ---------------------------------------------------------------------------
-- Carrito (un carrito "activo" por usuario, modelado como items)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cart_items (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    product_id  INTEGER NOT NULL REFERENCES products (id),
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, product_id)   -- idempotencia: add_to_cart hace UPSERT
);

CREATE INDEX IF NOT EXISTS idx_cart_user ON cart_items (user_id);

-- ---------------------------------------------------------------------------
-- Tickets de soporte (acción create_ticket del agente)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tickets (
    id              SERIAL PRIMARY KEY,
    ticket_number   TEXT UNIQUE NOT NULL,
    user_id         TEXT NOT NULL,
    subject         TEXT NOT NULL,
    body            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    related_order   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets (user_id);

-- ---------------------------------------------------------------------------
-- RAG: chunks de documentos (políticas/FAQs y, opcionalmente, productos)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_chunks (
    id           SERIAL PRIMARY KEY,
    source       TEXT NOT NULL,           -- nombre del doc o 'product:<sku>'
    doc_type     TEXT NOT NULL DEFAULT 'policy'
                 CHECK (doc_type IN ('policy', 'product', 'faq')),
    chunk_index  INTEGER NOT NULL,        -- orden del chunk dentro del doc
    content      TEXT NOT NULL,           -- texto original del chunk (para citaciones)
    embedding    VECTOR(1024),            -- Titan Text v2
    metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, chunk_index)          -- ingesta idempotente (re-correr no duplica)
);

-- Índice ANN para búsqueda por similitud coseno.
-- HNSW: buen recall/latencia; se puede crear sobre la tabla vacía.
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_chunks_source ON document_chunks (source);
