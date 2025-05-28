from fastapi import APIRouter, Body, HTTPException, Query, UploadFile, File
import json
from fastapi import Form
from fastapi.responses import FileResponse
from typing import Literal, Optional
import logging
from pydantic import BaseModel, Field
from pathlib import Path
from app.indexing.search_service import search_lessons, IndexStore
from app.services.llm_service import generate_llm_response
from app.services.cms_service import (
    load_lesson_by_path,
    load_metadata_by_path,
    get_lesson_pdf_path,
    list_all_lessons,
)

from app.services.llm_parser import extract_pdf_to_json
from app.core.config import BUCKET, s3


router = APIRouter()
logger = logging.getLogger(__name__)


class QARequest(BaseModel):
    question: str
    top_k: int = Field(default=3, ge=1, le=20, description="Must be between 1 and 20")
    lang: Literal["en", "es"] = "es"
    mode: Literal["explain", "reflect", "apply", "summarize", "ask"] = "explain"


@router.get("/quarters")
def list_quarters():
    """
    Returns a list of available quarters across all years.
    Example response: [{"year": "2025", "quarter": "Q2"}, ...]
    """
    try:
        lessons = list_all_lessons()
        # Extract unique (year, quarter) pairs
        quarters_set = set((l.get("year"), l.get("quarter")) for l in lessons)
        # Build sorted list
        quarters = [{"year": y, "quarter": q} for (y, q) in sorted(quarters_set)]
        return quarters
    except Exception as e:
        logger.error(f"Error listing quarters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to list quarters")


@router.get("/ping")
def ping():
    status = {
        "faiss_index_loaded": IndexStore.index is not None,
        "metadata_loaded": isinstance(IndexStore.metadata, list)
        and len(IndexStore.metadata) > 0,
    }
    return (
        {"status": "ok", **status}
        if all(status.values())
        else {"status": "error", **status}
    )


@router.get("/lessons/{year}/{quarter}/{lesson_id}")
def get_lesson(year: str, quarter: str, lesson_id: str):
    """
    Returns the full lesson.json file for a given year, quarter, and lesson ID.
    Example: /api/v1/lessons/2025/Q2/lesson_06
    """
    try:
        return load_lesson_by_path(year, quarter, lesson_id)
    except FileNotFoundError:
        logger.error(f"Lesson not found: {year}/{quarter}/{lesson_id}")
        raise HTTPException(status_code=404, detail="Lesson not found")


@router.get("/lessons/{year}/{quarter}/{lesson_id}/metadata")
def get_lesson_metadata(year: str, quarter: str, lesson_id: str):
    """
    Returns the metadata.json file for a given year, quarter, and lesson ID.
    Example: /api/v1/lessons/2025/Q2/lesson_06/metadata
    """
    try:
        return load_metadata_by_path(year, quarter, lesson_id)
    except FileNotFoundError:
        logger.error(f"Metadata not found: {year}/{quarter}/{lesson_id}")
        raise HTTPException(status_code=404, detail="Metadata not found")
    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Internal server error: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error loading metadata")


@router.get("/lessons/{year}/{quarter}/{lesson_id}/pdf")
def get_lesson_pdf(year: str, quarter: str, lesson_id: str):
    """
    Returns the PDF file for a given year, quarter, and lesson ID.
    Example: /api/v1/lessons/2025/Q2/lesson-08/pdf
    """
    try:
        pdf_path = get_lesson_pdf_path(year, quarter, lesson_id)
        return FileResponse(
            pdf_path, media_type="application/pdf", filename=f"{lesson_id}.pdf"
        )
    except FileNotFoundError:
        logger.error(f"PDF not found: {year}/{quarter}/{lesson_id}")
        raise HTTPException(status_code=404, detail="PDF file not found")
    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Internal server error: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error loading PDF")


@router.get("/lessons")
def list_lessons(
    year: Optional[str] = Query(None, description="Filter by year, e.g. '2025'"),
    quarter: Optional[str] = Query(None, description="Filter by quarter, e.g. 'Q2'"),
):
    """
    Returns lessons, optionally filtered by year and quarter.
    Examples:
      /api/v1/lessons
      /api/v1/lessons?year=2025&quarter=Q2
    """
    try:
        lessons = list_all_lessons()
        # Apply filters if provided
        if year:
            lessons = [l for l in lessons if l.get("year") == year]
        if quarter:
            lessons = [l for l in lessons if l.get("quarter") == quarter]
        return lessons
    except Exception as e:
        logger.error(f"Error listing lessons: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to list lessons")


@router.post("/llm")
def process_llm(
    text: str = Body(..., embed=True),
    mode: Literal["explain", "reflect", "apply", "summarize", "ask"] = Body(
        ..., embed=True
    ),
    lang: str = Query("en", description="Response language, e.g. 'en' or 'es'"),
):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty.")
    try:
        result = generate_llm_response(text, mode, "", lang)
        return {"result": result}
    except Exception as e:
        logger.error(f"Error processing LLM request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
def semantic_search(
    q: str = Query(..., description="Search query text"),
    type: str = Query(
        "all", description="Filter by document type: 'lesson', 'book', or 'all'"
    ),
    top_k: int = Query(5, ge=1, le=20, description="Number of top results to return"),
):
    """
    Semantic search through lessons and books using FAISS.
    """
    if not q or not q.strip():
        raise HTTPException(status_code=422, detail="Query string cannot be empty.")

    try:
        raw_results = search_lessons(q, top_k=top_k)

        if type.lower() in ["lesson", "book"]:
            filtered = [r for r in raw_results if r.get("type") == type.lower()]
        else:
            filtered = raw_results

        filtered = sorted(
            filtered, key=lambda x: x.get("normalized_score", 0), reverse=True
        )
        return {"query": q, "results": filtered, "count": len(filtered), "filter": type}

    except Exception as e:
        logger.error(f"Error during semantic search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm/answer")
def generate_answer(payload: QARequest):
    """
    Generates a response for a given question.
    1. Searches for relevant lessons using the question as a query.
    2. Combines the lesson fragments into a single text.
    3. Generates a response using the LLM model.
    Example: /api/v1/llm/answer
    Body: {
        "question": "What does justification by faith mean?",
        "top_k": 3,
        "lang": "es",
        "mode": "explain",
    }
    """
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    try:
        context_chunks = search_lessons(payload.question, top_k=payload.top_k)
        # 2a. Collect RAG references and raw texts
        rag_refs: dict[str, str] = {}
        formatted_chunks: list[str] = []
        for idx, chunk in enumerate(context_chunks):
            text = chunk.get("text", "")
            ref = None
            if chunk.get("type") == "book-section":

                ref = {
                    "book_title": chunk.get("book_title", ""),
                    "section_number": chunk.get("section_number", ""),
                    "section_title": chunk.get("section_title", ""),
                    "page_number": chunk.get("page_number", ""),
                }
            elif chunk.get("type") == "lesson-section":
                ref = {
                    "lesson_number": chunk.get("lesson_number", ""),
                    "title": chunk.get("title", ""),
                    "day_title": chunk.get("day_title", ""),
                    "day_index": chunk.get("day_index", ""),
                }
            if ref:
                rag_refs[str(idx)] = ref
            formatted_chunks.append(text)

        # 2b. Build the combined context text
        context_text = "\n\n".join(formatted_chunks)

        if not context_chunks:
            raise HTTPException(
                status_code=404,
                detail="No se encontró contexto relevante para esta pregunta.",
            )
        # 3. generate_llm_response
        response = generate_llm_response(
            payload.question, payload.mode, context_text, payload.lang
        )

        return {
            "question": payload.question,
            "answer": response.get("answer", ""),
            "context_used": len(context_chunks),
            "rag_refs": rag_refs,
            "other_refs": response.get("refs", ""),
        }

    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        raise HTTPException(status_code=400, detail=f"Error de validación: {str(ve)}")
    except Exception as e:
        logger.error(f"Internal server error: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/llm/parser")
async def parse_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF, extract its content to markdown, and return it as plain text.
    """
    # Save uploaded file to a temporary location
    temp_path = Path("/tmp") / file.filename
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Extract JSON data from PDF
    result = extract_pdf_to_json(str(temp_path), pages=None, page_chunks=True)

    # Build markdown output from chunks (ignore metadata)
    chunks = result.get("chunks", [])
    md_lines: list[str] = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            text = chunk.get("text", "")
        else:
            text = str(chunk)
        md_lines.append(text)
    markdown_content = "\n\n".join(md_lines)

    # Optionally clean up temp file
    try:
        temp_path.unlink()
    except Exception:
        pass

    # Return the generated markdown
    return {"markdown": markdown_content}


# Endpoint to import a cleaned lesson JSON and its PDF
@router.post("/lessons/{year}/{quarter}/{lesson_id}/import")
async def import_lesson(
    year: str,
    quarter: str,
    lesson_id: str,
    lesson_data: str = Form(..., description="Cleaned lesson JSON as string"),
    pdf: UploadFile = File(..., description="The lesson PDF file"),
):
    """
    Imports a cleaned lesson by saving lesson.json and PDF directly to S3 under {year}/{quarter}/{lesson_id}.
    Expects multipart/form-data with fields 'lesson_data' (JSON string) and 'pdf' (file).
    """
    logger.info(f"Importing lesson {lesson_id} for {year}/{quarter}")

    # Parse the JSON string payload into a dict
    try:
        data = json.loads(lesson_data)
        # In case lesson_data was double-encoded, decode again
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                # leave data as-is if it's not valid JSON
                pass
    except json.JSONDecodeError as e:
        logger.error(f"Invalid lesson JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid lesson JSON payload")

    # Save JSON directly to S3
    try:
        json_body = json.dumps(data, ensure_ascii=False, indent=2)
        json_key = f"{year}/{quarter}/{lesson_id}/lesson.json"
        s3.put_object(
            Bucket=BUCKET,
            Key=json_key,
            Body=json_body,
            ContentType="application/json",
        )
    except Exception as e:
        logger.error(f"Error uploading lesson JSON to S3: {e}")
        raise HTTPException(
            status_code=500, detail="Could not upload lesson JSON to S3"
        )

    # Read and upload PDF directly to S3
    try:
        pdf_contents = await pdf.read()
        pdf_key = f"{year}/{quarter}/{lesson_id}/{lesson_id}.pdf"
        s3.put_object(
            Bucket=BUCKET,
            Key=pdf_key,
            Body=pdf_contents,
            ContentType="application/pdf",
        )
    except Exception as e:
        logger.error(f"Error uploading PDF file to S3: {e}")
        raise HTTPException(status_code=500, detail="Could not upload PDF file to S3")

    return {
        "status": "ok",
        "message": f"Lesson '{lesson_id}' imported to S3 at {year}/{quarter}/{lesson_id}",
    }
