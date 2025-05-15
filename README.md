# Sabbath School Study App – Backend

This document describes the backend for the Interactive Sabbath School Study application.

## Table of Contents

1. Overview
2. Tech Stack & Dependencies
3. Project Structure
4. Prerequisites & Environment Variables
5. Setup & Installation
6. Running Locally (Make Commands)
7. Docker Compose Setup
8. API Endpoints & Schemas

   - Health Check (/ping)
   - Lesson Content
   - Metadata
   - PDF
   - Semantic Search
   - LLM Endpoints
   - Admin (Reindex & Status)

9. Data Schemas

   - Lesson JSON
   - Metadata JSON
   - Search Result Object
   - LLM Request/Response
   - QA Request/Response

10. Prompt Templates
11. Testing
12. Contributing

---

## 1. Overview

The backend is a FastAPI application providing:

- Traditional Sabbath School lesson navigation (day-by-day JSON + PDF)
- Semantic search over lessons & indexed EGW books (FAISS)
- Retrieval-augmented LLM endpoints (explain, reflect, apply, summarize, ask)
- Admin endpoints to build/reload the FAISS index
- Health check for readiness

## 2. Tech Stack & Dependencies

- **Python 3.11+**
- **FastAPI**
- **Uvicorn** (ASGI server)
- **FAISS** (vector index)
- **sentence-transformers** (embeddings)
- **python-jose** (JWT, if enabled)
- **requests** (Bible API calls)
- **pydantic-settings** (environment vars)

Dependencies list in `requirements.txt`.

## 3. Project Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py        # BaseSettings loader
│   │   └── security.py      # X-API-Key auth dependency
│   │
│   ├── indexing/
│   │   ├── embeddings.py    # embed_text()
│   │   ├── index_builder.py # build_index script
│   │   └── search_service.py# IndexStore, preload, search_lessons()
│   │
│   ├── prompts/            # .txt templates per mode
│   │   ├── explain.txt
│   │   ├── reflect.txt
│   │   ├── apply.txt
│   │   ├── summarize.txt
│   │   └── ask.txt
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── routes.py         # public endpoints (/lessons, /search, /llm)
│   │       └── admin_routes.py   # protected admin endpoints
│   │
│   ├── services/
│   │   ├── cms_service.py  # load_lesson_by_path, load_metadata, get_pdf
│   │   └── llm_service.py  # generate_llm_response()
│   │
│   ├── data/              # lesson/book JSON + PDFs
│   │   ├── 2025/Q2/...
│   │   └── books/*.json
│   │
│   ├── main.py            # FastAPI app + lifespan preload
│   ├── Dockerfile
│   └── docker-compose.yml
├── tests/                 # pytest test suite
├── requirements.txt
└── Makefile
```

## 4. Prerequisites & Environment Variables

Create a `.env` in `backend/` with:

```
ADMIN_KEY=your-secure-api-key
ADMIN_USERNAME=teacher_username    # optional, defaults to "admin"
# GEMINI_API_KEY=...               # if using Google Gemini
# Other keys as needed
```

## 5. Setup & Installation

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Running Locally (Make Commands)

```Makefile
serve-local:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
index:
	python app/indexing/index_builder.py
	# moves index files under app/indexing/
```

Use:

```bash
make serve-local
make index
```

## 7. Docker Compose Setup

```yaml
version: "3.8"
services:
  fastapi:
    build: .
    ports:
      - "8000:8000"
    env_file: [".env"]
    volumes:
      - ./app:/app
```

Bring up:

```bash
docker-compose up --build
```

## 8. API Endpoints & Schemas

### Health Check

**GET** `/api/v1/ping`

```json
{
  "status": "ok",
  "faiss_index_loaded": true,
  "metadata_loaded": true
}
```

### Lesson Content

**GET** `/api/v1/lessons/{year}/{quarter}/{lesson_id}`

- Returns raw `lesson.json` structure.

### Metadata

**GET** `/api/v1/lessons/{year}/{quarter}/{lesson_id}/metadata`

- Returns parsed `metadata.json`.

### PDF

**GET** `/api/v1/lessons/{year}/{quarter}/{lesson_id}/pdf`

- Returns PDF file response.

### Semantic Search

**GET** `/api/v1/search?q=<query>&type=[all|lesson|book]&top_k=<n>`

- Returns:

```json
{
  "query": "<query>",
  "results": [ { ...SearchResult }, ... ],
  "count": n,
  "filter": "all"
}
```

### LLM – Generic

**POST** `/api/v1/llm?lang=<en|es>`
Body:

```json
{ "text": "...", "mode": "explain|reflect|apply|summarize|ask" }
```

Response:

```json
{ "result": <string> }
```

### LLM – Q\&A

**POST** `/api/v1/llm/answer`
Body:

```json
{ "question": "...", "top_k": 3, "lang": "es" }
```

Response:

```json
{ "question": "...",
  "answer": "...",
  "context_used": 3,
  "rag_refs": { "0": "Lesson-6-...", ... }
}
```

### Admin – Protected by X-API-Key

**POST** `/api/v1/admin/reindex`
Header: `X-API-Key: your-secure-api-key`
Response:

```json
{ "status": "reindexed", "index_loaded": true, "metadata_loaded": true }
```

**GET** `/api/v1/admin/status`
Header: `X-API-Key: ...`

```json
{ "index_loaded": true, "metadata_count": 513 }
```

## 9. Data Schemas

### Lesson JSON (`lesson.json`)

```jsonschema
{
  "lesson": {
    "id": "leccion_6_...",
    "lesson_number": integer,
    "week_start_date": "YYYY-MM-DD",
    "week_end_date": "YYYY-MM-DD",
    "daily_sections": [
      {
        "id": string,
        "lesson_number": integer,
        "day_index": integer,
        "day_title": string,
        "content": [string,...]
      }
    ]
  }
}
```

### Metadata JSON (`metadata.json`)

```jsonschema
{
  "title": string,
  "summary": string,
  "week_start_date": "YYYY-MM-DD",
  "week_end_date": "YYYY-MM-DD",
  "lesson_number": integer,
  "day_titles": [string,...]
}
```

### Search Result Object

```jsonschema
{
  "type": "lesson-section" | "book-section",
  "source": string,
  "lesson_id"?: string,
  "lesson_number"?: integer,
  "title"?: string,
  "day_index"?: integer,
  "day_title"?: string,
  "book_title"?: string,
  "page_number"?: string,
  "text": string,
  "score": float,
  "normalized_score": float,
  "error"?: string
}
```

### LLM Generic Request/Response

```jsonschema
# Request
{ "text": string, "mode": string }
# Response
{ "result": string }
```

### Q\&A Request/Response

```jsonschema
# Request
{ "question": string,
  "top_k": integer,
  "lang": "en" | "es" }
# Response
{ "question": string,
  "answer": string,
  "context_used": integer,
  "rag_refs": { [index]: string }
}
```

## 10. Prompt Templates

Located in `app/prompts/`, one `.txt` per mode:

- explain.txt
- reflect.txt
- apply.txt
- summarize.txt
- ask.txt

Each uses `{context}`, `{question}`, `{lang}` placeholders.

## 11. Testing

- Run unit & integration tests:

  ```bash
  pytest -v
  ```

- Run only search tests:

  ```bash
  pytest tests/test_search_service.py::test_ping_status -v
  ```

## 12. Contributing

Feel free to submit PRs for:

- Adding cohorts & dashboard features
- Improving prompt templates
- Multi‑language support
