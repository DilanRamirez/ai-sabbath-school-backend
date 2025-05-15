import os
import json
import faiss
import numpy as np
from pathlib import Path
from app.indexing.embeddings import embed_text

# Output locations
OUTPUT_DIR = Path(__file__).resolve().parent
INDEX_FILE = OUTPUT_DIR / "lesson_index.faiss"
METADATA_FILE = OUTPUT_DIR / "lesson_index_meta.json"

# Input directories
LESSON_DIR = OUTPUT_DIR.parent / "data"
BOOK_DIR = LESSON_DIR / "books"


def build_index():
    print("🔍 Building index...")
    texts = []
    metadata = []

    # --- Index Lessons (by daily section) ---
    for root, dirs, files in os.walk(LESSON_DIR):
        for file in files:
            if file != "lesson.json":
                continue

            path = os.path.join(root, file)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    lesson = data.get("lesson", {})
                    sections = lesson.get("daily_sections", [])

                    for i, section in enumerate(sections):
                        content_list = section.get("content", [])
                        text = " ".join(content_list).strip()
                        quote_list = section.get("quotes", [])
                        if isinstance(quote_list, list):
                            quote_list = [str(q["text"]) for q in quote_list]
                            if not text:
                                continue
                        quote_text = " ".join(quote_list).strip()

                        texts.append(text)
                        metadata.append(
                            {
                                "type": "lesson-section",
                                "lesson_id": lesson.get("id"),
                                "lesson_number": lesson.get("lesson_number"),
                                "title": lesson.get("title"),
                                "day_date": section.get("date"),
                                "day": section.get("day"),
                                "day_index": i + 1,
                                "day_title": section.get("title", f"Section {i+1}"),
                                "source": path,
                                "text": text,
                                "quote": quote_text,
                            }
                        )

            except Exception as e:
                print(f"⚠️ Skipping lesson {path}: {e}")

    # --- Index all JSON files under BOOK_DIR ---
    if BOOK_DIR.exists():
        for json_path in BOOK_DIR.rglob("*.json"):
            print(f"📖 Indexing JSON: {json_path.name}")
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                # If this JSON defines sections, index each item
                if isinstance(data, dict) and "sections" in data:
                    for sec in data["sections"]:
                        sec_num = sec.get("section_number", "")
                        for item in sec.get("items", []):
                            title = item.get("title", "")
                            page = item.get("page")
                            content_list = item.get("content", [])
                            # join list of paragraphs into one text block
                            text = (
                                " ".join(content_list).strip()
                                if isinstance(content_list, list)
                                else str(content_list).strip()
                            )
                            if not text:
                                continue
                            texts.append(text)
                            metadata.append(
                                {
                                    "type": "book-section",
                                    "book_title": data.get("title", ""),
                                    "book_author": data.get("author", ""),
                                    "section_number": sec_num,
                                    "section_title": sec.get("section_title", ""),
                                    "page_start": sec.get("page_start"),
                                    "page_end": sec.get("page_end"),
                                    "item_title": title,
                                    "page_number": page,
                                    "source": str(json_path),
                                    "text": text,
                                    "book-section-id": item.get("book-section-id", ""),
                                }
                            )
                else:
                    # Fallback: flat JSON with a "content" or "text" field
                    flat = data.get("content") or data.get("text") or ""
                    if isinstance(flat, list):
                        text = " ".join(flat).strip()
                    else:
                        text = str(flat).strip()
                    if text:
                        texts.append(text)
                        metadata.append(
                            {
                                "type": "json-flat",
                                "file_name": json_path.stem,
                                "source": str(json_path),
                            }
                        )
            except Exception as e:
                print(f"⚠️ Skipping JSON {json_path.name}: {e}")

    # --- Final check ---
    if not texts:
        print("⚠️ No documents found to index. Exiting.")
        return

    print(f"✅ Found {len(texts)} content chunks. Embedding...")

    vectors = [embed_text(t) for t in texts]
    index = faiss.IndexFlatL2(len(vectors[0]))
    index.add(np.array(vectors).astype("float32"))

    print("💾 Writing index and metadata...")
    faiss.write_index(index, str(INDEX_FILE))
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ Successfully indexed {len(texts)} chunks.")
    print(f"📁 Index: {INDEX_FILE}")
    print(f"📁 Metadata: {METADATA_FILE}")


if __name__ == "__main__":
    build_index()
