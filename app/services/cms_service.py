from pathlib import Path
import json
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent / "data"


def load_lesson_by_path(year: str, quarter: str, lesson_id: str) -> dict[str, Any]:
    """
    Loads a lesson given its path structure: /data/{year}/{quarter}/{lesson_id}/lesson.json
    """
    lesson_path = BASE_DIR / year / quarter / lesson_id / "lesson.json"
    if not lesson_path.exists():
        raise FileNotFoundError(f"Lesson file not found at {lesson_path}")

    with open(lesson_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_metadata_by_path(year: str, quarter: str, lesson_id: str) -> dict[str, Any]:
    """
    Loads metadata.json from the lesson folder.
    Guards:
    - Year, quarter, lesson_id must be safe strings
    - File must exist
    - JSON must be valid
    """
    if not all([year, quarter, lesson_id]):
        raise ValueError("Missing one or more required path parameters")

    metadata_path = BASE_DIR / year / quarter / lesson_id / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found at {metadata_path}")

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in {metadata_path}")


def get_lesson_pdf_path(year: str, quarter: str, lesson_id: str) -> Path:
    if not all([year, quarter, lesson_id]):
        raise ValueError("Missing one or more required path parameters")

    pdf_path = BASE_DIR / year / quarter / lesson_id / "lesson.pdf"

    print(f"[DEBUG] Looking for PDF at: {pdf_path}")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at {pdf_path}")

    return pdf_path


def list_all_lessons() -> list[dict[str, Any]]:
    """
    Scans the lesson directory structure and loads metadata for each lesson.
    Guards:
    - Only returns folders that have metadata.json
    - Skips unreadable or malformed folders
    """
    lessons = []
    print(f"[DEBUG] Scanning for lessons in {BASE_DIR}")

    for year_dir in BASE_DIR.iterdir():
        print(f"[DEBUG] Checking year directory: {year_dir}")
        if not year_dir.is_dir():
            continue

        for quarter_dir in year_dir.iterdir():
            if not quarter_dir.is_dir():
                continue

            for lesson_dir in quarter_dir.iterdir():
                if not lesson_dir.is_dir():
                    continue

                metadata_path = lesson_dir / "metadata.json"
                if not metadata_path.exists():
                    continue

                try:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        lessons.append(
                            {
                                "year": year_dir.name,
                                "quarter": quarter_dir.name,
                                "lesson_id": lesson_dir.name,
                                "metadata": metadata,
                            }
                        )
                except Exception as e:
                    print(f"Skipping {lesson_dir} due to error: {e}")
                    continue

    return lessons
