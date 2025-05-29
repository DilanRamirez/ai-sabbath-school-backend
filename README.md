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

The Sabbath School backend is a containerized FastAPI service providing:

- **Content Management** for Sabbath School lessons (JSON metadata, PDF files)
- **Semantic Search** over lessons and indexed books via FAISS
- **LLM-Powered Tools** for explain, reflect, apply, summarize, ask, and PDF-to-Markdown parsing
- **Import Workflow** for cleaned lesson JSON + PDF uploads
- **S3 Storage** of all lesson assets (JSON + PDF)
- **Admin Routes** for reindexing and maintenance, secured via an API key

It is designed for scalability (Docker + Docker Compose), testability (pytest + moto + CI), and easy deployment (Railway, Vercel, or other container hosts).

---

## 2. Technology Stack

- **Language & Framework**: Python 3.11+, FastAPI
- **API Server**: Uvicorn, with hot-reload in development
- **Storage**

  - **Amazon S3** via Boto3 for JSON & PDF objects
  - **FAISS** for vector search index (stored locally or in container volume)

- **LLM Integration**: Google Gemini (via google-generative-ai)
- **Authentication**:

  - **X-API-Key** for admin routes
  - JWT or similar can be added for user roles

- **Testing**: pytest, moto (S3 mocking), TestClient
- **CI/CD**: GitHub Actions for lint, format, tests; Docker Compose for local dev; container registry for production
- **Configuration**: Pydantic v2 Settings, `.env` for secrets

Dependencies list in `requirements.txt`.

---

## 3. Configuration & Environment

| Variable                | Description                                |
| ----------------------- | ------------------------------------------ |
| `S3_BUCKET`             | Name of the S3 bucket for lessons & PDFs   |
| `AWS_ACCESS_KEY_ID`     | IAM user access key                        |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key                        |
| `AWS_REGION`            | AWS region (e.g. `us-east-1`)              |
| `GEMINI_API_KEY`        | Google Generative AI API key               |
| `ADMIN_KEY`             | X-API-Key for admin endpoints              |
| `ADMIN_USERNAME`        | Username for admin JWT (optional)          |
| `ADMIN_PASSWORD`        | Password for admin JWT (optional)          |
| `JWT_SECRET`            | Secret for signing JWTs (if JWT auth used) |
| `DEBUG`                 | `true`/`false` for development mode        |

All are loaded via a Pydantic `Settings` class in `app/core/config.py`, and `boto3.client` is instantiated unconditionally so tests can monkey-patch it.

## 4. Project Structure

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

## 5. Prerequisites & Environment Variables

Create a `.env` in `backend/` with:

```
ADMIN_KEY=your-secure-api-key
ADMIN_USERNAME=teacher_username    # optional, defaults to "admin"
# GEMINI_API_KEY=...               # if using Google Gemini
# Other keys as needed
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

---

## 5. API Endpoints

### 5.1 Public Lesson Retrieval

```
GET /api/v1/quarters
→ [ { year: "2025", quarter: "Q2" }, … ]
```

```
GET /api/v1/lessons?year={y}&quarter={q}
→ [ { year, quarter, lesson_id }, … ]
```

```
GET /api/v1/lessons/{year}/{quarter}/{lesson_id}
→ JSON lesson content
```

```
GET /api/v1/lessons/{year}/{quarter}/{lesson_id}/metadata
→ metadata.json (title, week_range, memory_verse…)
```

```
GET /api/v1/lessons/{year}/{quarter}/{lesson_id}/pdf
→ StreamingResponse(application/pdf)
```

All lesson routes fetch `lesson.json` or PDF from S3 using `config.s3.get_object(...)`.

### 5.2 Semantic Search

```
GET /api/v1/search
? q=<query>
& type=<lesson|book|all>         # optional filter
& top_k=<1–20>                   # default 5
→ { query, filter, count, results: [ { type, source, score, normalized_score, text }, … ] }
```

- Embeds `q` via `embed_text()`, searches FAISS, and returns nearest chunks with scores and extracted text.
- Automatically normalizes scores to 0–100%.

### 5.3 LLM Endpoints

```
POST /api/v1/llm
Body JSON { text, mode: one of ["explain","reflect","apply","summarize","ask"], lang: "en"|"es" }
→ { result: string | { answer, rag_refs?, … } }
```

```
POST /api/v1/llm/answer
Body JSON { question, top_k=3, lang="es" }
→ { question, answer, context_used }
```

```
POST /api/v1/llm/parser
multipart/form-data file field: file
→ { markdown: string }
```

- All LLM calls funnel through `generate_llm_response`, which builds precise prompts, handles Bible reference expansion (via Bible-API), and enforces language/tone.

### 5.4 Import & Admin

```
POST /api/v1/lessons/{year}/{quarter}/{lesson_id}/import
Form fields:
  - lesson_data: JSON string
  - pdf: UploadFile
→ { status: "ok", message: … }
```

- Saves both JSON and PDF to S3 under `{year}/{quarter}/{lesson_id}/…`

```
POST /api/v1/admin/reindex
Header X-API-Key: <ADMIN_KEY>
→ { status: "reindex started" }
```

```
GET /api/v1/admin/status
Header X-API-Key: <ADMIN_KEY>
→ { status: "idle" | "building" }
```

Admin routes use a dependency that checks `X-API-Key` against `settings.ADMIN_KEY`.

---

## 6. Indexing & Search Workflow

1. **Index Building**

   - `python app/indexing/index_builder.py` (or Docker `make index`)
   - Walks lesson folders + `data/books/*.json`, embeds chunks, writes `lesson_index.faiss` and metadata JSON.

2. **App Startup Preload**

   - FastAPI lifespan event calls `IndexStore.preload_index_and_metadata()`
   - Loads FAISS index into memory once per process.

3. **Querying**

   - Each `/search` call uses `IndexStore.index.search(...)`.

---

## 7. Error Handling & Validation

- **Pydantic** and FastAPI parameter validation guarantee 422 on missing/invalid query/form params.
- **Guard Clauses** across all routes: empty text, invalid modes, missing file, JSON decode errors (400), S3 not found (404), unexpected failures (500).
- **Structured Logging** with `logger.error(…, exc_info=True)` aids debugging.

---

## 8. Testing

- **Unit & Integration** with pytest and Starlette’s `TestClient`.
- **S3 Mocking** via moto’s `mock_aws()` fixture.
- **FAISS Mocking** by patching `IndexStore.index = None` or providing dummy vectors.
- **LLM Stubs** via `monkeypatch` on `generate_llm_response` and `extract_pdf_to_json`.
- **Coverage**

  - CMS service loading errors, empty and malformed inputs
  - All route success/failure paths (422, 404, 400, 500)
  - Admin authentication success/failure

---

## 9. CI/CD & Deployment

- **GitHub Actions**

  - `lint-backend`, `format-backend` (Black), `test-backend`
  - Docker build + test, push to container registry

- **Railway / Heroku / ECS / Fly.io**

  - Environment variables configured in project settings
  - Deployment triggers automatic reindex if needed

- **Docker Compose** for local orchestration

  - `backend` service with mounted volumes for `data/`, index, and `.env`

---

## 12. Contributing

Feel free to submit PRs for:

- Adding cohorts & dashboard features
- Improving prompt templates
- Multi‑language support
