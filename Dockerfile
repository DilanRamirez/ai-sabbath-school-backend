# backend/Dockerfile

FROM python:3.11-slim

# Set workdir
WORKDIR /app
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY ./app ./app
COPY requirements.txt .
COPY .env .env

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose port
EXPOSE 8000


CMD ["sh", "-c", "python app/indexing/index_builder.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]