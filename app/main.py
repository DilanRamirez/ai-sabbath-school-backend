from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.indexing.search_service import preload_index_and_metadata
from app.api.v1.routes import router as api_router  # your public routes
from app.api.v1.admin_routes import router as admin_router  # admin‐only
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load FAISS index + metadata once at startup
    preload_index_and_metadata()
    yield
    # (optional teardown)


app = FastAPI(lifespan=lifespan)

# Public endpoints (search, LLM, lessons, etc.)
app.include_router(api_router, prefix="/api/v1")

# Admin endpoints, protected by X-API-Key
app.include_router(admin_router, prefix="/api/v1/admin")


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}", "debug": settings.DEBUG}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/ping")
def ping():
    return {"status": "pong"}
