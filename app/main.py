from fastapi import FastAPI
from fastapi import Depends
from app.core.security import get_current_user, require_role
import os
import json
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.indexing.search_service import preload_index_and_metadata
from app.api.v1.routes import router as api_router  # your public routes
from app.api.v1.admin_routes import router as admin_router  # admin‐only
from app.api.v1.auth import router as auth_router  # auth routes
from app.api.v1.study import router as study_router  # study progress routes
from app.api.v1.bible import router as bible_router  # Bible API routes
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load FAISS index + metadata once at startup
    preload_index_and_metadata()
    yield
    # (optional teardown)


app = FastAPI(lifespan=lifespan)

# Allow CORS from specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3004",
        "https://ai-sabbath-school-frontend.vercel.app",
        "https://gentle-meadow-08f54890f.6.azurestaticapps.net",
    ],
    allow_origin_regex=r"https://.*\.azurestaticapps\.net",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public endpoints (search, LLM, lessons, etc.)
app.include_router(
    api_router, prefix="/api/v1", dependencies=[Depends(get_current_user)]
)

# Admin endpoints, protected by X-API-Key and admin role
app.include_router(
    admin_router, prefix="/api/v1/admin", dependencies=[Depends(require_role("admin"))]
)

# Auth endpoints
app.include_router(auth_router, prefix="/api/v1/auth")

# Study progress endpoints, require authentication
app.include_router(
    study_router, prefix="/api/v1/study", dependencies=[Depends(get_current_user)]
)

# Bible API endpoints, require authentication
app.include_router(
    bible_router, prefix="/api/v1/bible", dependencies=[Depends(get_current_user)]
)


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}", "debug": settings.DEBUG}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/ping")
def ping():
    return {"status": "pong"}
