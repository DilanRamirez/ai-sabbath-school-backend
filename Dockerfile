# ====== Builder Stage ======
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build‑only dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code & build the FAISS index
COPY . .
RUN python -m app.indexing.index_builder \
    && mkdir -p /index \
    && mv app/indexing/lesson_index.faiss /index/ \
    && mv app/indexing/lesson_index_meta.json /index/

# ====== Runtime Stage ======
FROM python:3.11-slim

WORKDIR /app

# Copy only the installed deps from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only the code (minus heavy data/index)
COPY app app
COPY Dockerfile docker-compose.yml requirements.txt ./

# Copy the pre-built index
COPY --from=builder /index /app/app/indexing

# Install runtime OS‑level deps if needed (keep to a minimum)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]