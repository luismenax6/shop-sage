# Backend image. Built from the REPO ROOT so it can include the dataset (data/
# lives at the repo root) for the one-off DB bootstrap task. The image mirrors
# the repo layout (/app/backend + /app/data) so the seed/ingest scripts resolve
# their paths the same as locally. The C extension (csim) is compiled here —
# this is why the backend runs on ECS Fargate and not Lambda.
#
#   docker build -f backend/Dockerfile -t <tag> .      # run from the repo root
FROM python:3.12-slim

# Build tools for the C extension (build-essential pulls gcc + libc headers) +
# libpq for psycopg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Install Python deps first for better layer caching.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Build and install the C extension.
COPY backend/csim/ ./csim/
RUN pip install --no-cache-dir ./csim

# App, schema, scripts, entrypoint.
COPY backend/app/ ./app/
COPY backend/db/ ./db/
COPY backend/scripts/ ./scripts/
COPY backend/wsgi.py .

# Dataset, for the one-off bootstrap task (mirrors the repo: /app/data).
COPY data/ /app/data/

EXPOSE 5000

# DATABASE_URL is injected by ECS from Secrets Manager at runtime.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "wsgi:app"]
