# Backend image. The C extension (csim) is compiled here at build time — this is
# why the backend runs on ECS Fargate and not Lambda.
FROM python:3.12-slim

# Build tools for the C extension + libpq for psycopg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Build and install the C extension.
COPY csim/ ./csim/
RUN pip install --no-cache-dir ./csim

# App code.
COPY app/ ./app/
COPY wsgi.py .

EXPOSE 5000

# DATABASE_URL is injected by ECS from Secrets Manager at runtime.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "wsgi:app"]
