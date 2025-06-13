from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
import logging

from app.core.security import get_api_key
from app.indexing.search_service import preload_index_and_metadata, IndexStore

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(get_api_key)],
)


@router.post("/reindex")
def reindex():
    """
    Trigger a full rebuild of the FAISS index and metadata.
    """
    try:
        logger.info("🔄 Admin triggered reindex()")
        preload_index_and_metadata()
        logger.info(f"✅ Reindex complete: {len(IndexStore.metadata)} chunks loaded")
        return JSONResponse(
            content={
                "status": "reindexed",
                "index_loaded": IndexStore.index is not None,
                "metadata_loaded": bool(IndexStore.metadata),
            }
        )
    except Exception as e:
        logger.error(f"Error during reindex: {e}")
        raise HTTPException(status_code=500, detail=f"Reindex failed: {e}")


@router.get("/status")
def admin_status():
    """
    Returns current status of the FAISS index.
    """
    return JSONResponse(
        content={
            "index_loaded": IndexStore.index is not None,
            "metadata_count": len(IndexStore.metadata) if IndexStore.metadata else 0,
        }
    )
