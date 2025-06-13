import json
from fastapi import APIRouter, HTTPException
from pathlib import Path
import logging
from app.services.bible_service import parse_reference

SPANISH_BOOK_MAP = {
    "Gén.": "Génesis",
    "Génesis": "Génesis",
    "Éxo.": "Éxodo",
    "Éxodo": "Éxodo",
    "1 Tim.": "1 Timoteo",
    "1 Timoteo": "1 Timoteo",
    "2 Tim.": "2 Timoteo",
    "2 Timoteo": "2 Timoteo",
    # include other necessary abbreviations...
}


BIBLE_DATA_PATH = Path(__file__).parent.parent.parent / "bible" / "RVR1960.json"
router = APIRouter()
logger = logging.getLogger(__name__)

try:
    with open(BIBLE_DATA_PATH, "r", encoding="utf-8") as f:
        BIBLE = json.load(f)
except Exception as e:
    BIBLE = {}
    logger.error(f"Failed to load Bible JSON: {e}")


@router.get("/books")
def list_books():
    """Return all available book names."""
    available = list(BIBLE.keys())
    # Determine which books from the full canon are missing
    return {
        "books": available,
    }


@router.get("/{book}/{chapter}")
def get_chapter(book: str, chapter: str):
    """
    Return all verses for a given book and chapter.
    """
    book_data = BIBLE.get(book)
    if not book_data:
        raise HTTPException(status_code=404, detail="Book not found")
    chapter_data = book_data.get(chapter)
    if not chapter_data:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return {"book": book, "chapter": chapter, "verses": chapter_data}


@router.get("/{book}/{chapter}/{verse}")
def get_verse(book: str, chapter: str, verse: str):
    """
    Return a single verse text.
    """
    book_data = BIBLE.get(book)
    if not book_data:
        raise HTTPException(status_code=404, detail="Book not found")
    chapter_data = book_data.get(chapter)
    if not chapter_data:
        raise HTTPException(status_code=404, detail="Chapter not found")
    verse_text = chapter_data.get(verse)
    if not verse_text:
        raise HTTPException(status_code=404, detail="Verse not found")
    return {"book": book, "chapter": chapter, "verse": verse, "text": verse_text}


# New endpoint: parse a free-form biblical reference and return the corresponding verses or verse.
@router.get("/reference")
def get_reference(ref: str):
    """
    Parse a free-form biblical reference (e.g., 'Mateo 12:9-14', 'Juan 5:1-16', '2 Tim. 1:7')
    and return the corresponding verses or single verse. Also supports "Book Chapter" to return entire chapter.
    """
    # If no verse specified (no colon), treat as full chapter request
    if ":" not in ref:
        # Expect format "Book Chapter", split on last space
        try:
            book_part, chapter_part = ref.strip().rsplit(" ", 1)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid reference format; expected 'Book Chapter' or 'Book Chapter:Verse'",
            )

        raw_book = book_part.strip()
        book = SPANISH_BOOK_MAP.get(raw_book, raw_book)
        chapter = chapter_part.strip()

        # Lookup book and chapter
        book_data = BIBLE.get(book)
        if not book_data:
            raise HTTPException(status_code=404, detail=f"Book '{book}' not found")
        chapter_data = book_data.get(chapter)
        if not chapter_data:
            raise HTTPException(
                status_code=404, detail=f"Chapter '{chapter}' not found in '{book}'"
            )
        return {"book": book, "chapter": chapter, "verses": chapter_data}

    # Standard parsing with verses/ranges
    try:
        parsed = parse_reference(ref)
        raw_book = parsed["book"]
        book = SPANISH_BOOK_MAP.get(raw_book, raw_book)
        chapter = parsed["chapter"]
        start = parsed["verse_start"]
        end = parsed["verse_end"]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    book_data = BIBLE.get(book)
    if not book_data:
        raise HTTPException(status_code=404, detail=f"Book '{book}' not found")

    chapter_data = book_data.get(chapter)
    if not chapter_data:
        raise HTTPException(
            status_code=404, detail=f"Chapter '{chapter}' not found in '{book}'"
        )

    # If single verse
    if start == end:
        verse_text = chapter_data.get(start)
        if not verse_text:
            raise HTTPException(
                status_code=404, detail=f"Verse '{start}' not found in {book} {chapter}"
            )
        return {"book": book, "chapter": chapter, "verse": start, "text": verse_text}

    # Range of verses
    verses = {}
    for v in range(int(start), int(end) + 1):
        v_str = str(v)
        text = chapter_data.get(v_str)
        if text:
            verses[v_str] = text
    if not verses:
        raise HTTPException(
            status_code=404,
            detail=f"No verses found in range {start}-{end} for {book} {chapter}",
        )
    return {"book": book, "chapter": chapter, "verses": verses}
