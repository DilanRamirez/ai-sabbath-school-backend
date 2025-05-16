import faiss
import json
import numpy as np
from pathlib import Path
from typing import List
from app.indexing.embeddings import embed_text

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "lesson_index.faiss"
METADATA_FILE = BASE_DIR / "lesson_index_meta.json"


def load_faiss_index() -> faiss.Index:
    if not INDEX_FILE.exists():
        raise FileNotFoundError(f"Missing index file: {INDEX_FILE}")
    return faiss.read_index(str(INDEX_FILE))


def load_metadata() -> List[dict]:
    if not METADATA_FILE.exists():
        raise FileNotFoundError(f"Missing metadata file: {METADATA_FILE}")
    with open(str(METADATA_FILE), "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_score(score: float) -> float:
    return round(100 * (1 / (1 + score)), 2)


def load_chunk_text(meta: dict) -> str:
    try:
        with open(meta["source"], "r", encoding="utf-8") as f:
            data = json.load(f)

        if meta["type"] == "lesson-section":
            sections = data.get("lesson", {}).get("daily_sections", [])
            idx = meta.get("day_index")
            if idx is not None and 0 <= idx < len(sections):
                return " ".join(sections[idx].get("content", []))

        elif meta["type"] == "book-section":
            sections = data.get("sections", [])
            section_idx = meta.get("section_index", meta.get("section_number"))
            section = next(
                (s for s in sections if s.get("section_number") == section_idx), None
            )
            items = section.get("items", []) if section else []
            book_id = meta.get("book-section-id")

            found = next(
                (item for item in items if item.get(
                    "book-section-id") == book_id), None
            )
            if not found:
                page = meta.get("page_number")
                found = next(
                    (item for item in items if item.get("page") == page), None)

            return found.get("content", "") if found else meta.get("text", "")

        else:
            return data.get("content") or data.get("text", "")
    except Exception as e:
        return f"Error loading Contenido: {e}"


class IndexStore:
    index = None
    metadata = []


def preload_index_and_metadata():
    try:
        IndexStore.index = load_faiss_index()
        IndexStore.metadata = load_metadata()
    except Exception as e:
        print(f"[ERROR] Could not preload FAISS index: {e}")


def search_lessons(query: str, top_k: int = 5) -> List[dict]:
    if not query or not isinstance(query, str) or not query.strip():
        return [{"error": "Query is empty or invalid."}]

    try:
        if IndexStore.index is None or not IndexStore.metadata:
            raise RuntimeError("FAISS index or metadata not loaded in memory.")

        query_vector = embed_text(query)
        D, I = IndexStore.index.search(
            np.array([query_vector], dtype="float32"), top_k)

        results = []
        for score, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(IndexStore.metadata):
                continue

            meta = IndexStore.metadata[idx]
            score_value = float(score)
            results.append(
                {
                    **meta,
                    "score": score_value,
                    "normalized_score": normalize_score(score_value),
                    "text": load_chunk_text(meta),
                }
            )

        return results

    except Exception as e:
        return [{"error": str(e)}]
