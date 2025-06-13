import re
from PyPDF2 import PdfReader
import pandas as pd
import uuid
import json
import os


def normalize_paragraphs(text: str) -> str:
    """
    Normalize text from PDF extraction by:
    1. Merging hyphen-split words at line ends.
    2. Converting sentence-ending newlines before uppercase letters into paragraph breaks (double newlines).
    3. Collapsing other single newlines into spaces.
    4. Normalizing multiple spaces.
    """
    # 1) Merge hyphenated line breaks (e.g. 'llegó-\nta' -> 'llegóta')
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    # 2) Convert sentence-ending newline + uppercase start into paragraph break
    #    e.g. '...visitación."\nDesde...' -> '...visitación."\n\nDesde...'
    text = re.sub(r"([\.\?\!])\n(?=[A-ZÁÉÍÓÚÑ])", r"\1\n\n", text)

    # 3) Collapse other single newlines (not part of paragraph breaks) into spaces
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # 4) Normalize multiple spaces into a single space
    text = re.sub(r" +", " ", text)

    return text.strip()


def parse_toc_format_1(pdf_path):
    reader = PdfReader(pdf_path)
    # Extract first 15 pages for TOC
    text = "\n".join(
        reader.pages[i].extract_text() or "" for i in range(min(15, len(reader.pages)))
    )
    pattern = re.compile(r"^(.*?)\s*\.{3,}\s*(\d+)$", re.MULTILINE)
    entries = pattern.findall(text)

    return [(title.strip(), int(page)) for title, page in entries]


def parse_toc_format_2(pdf_path):
    reader = PdfReader(pdf_path)
    text = "\n".join(
        reader.pages[i].extract_text() or "" for i in range(min(15, len(reader.pages)))
    )
    # Roman numerals or Arabic
    pattern = re.compile(r"^(.*?)\s*\.{3,}\s*([IVXLC]+|\d+)$", re.MULTILINE)

    def roman_to_int(r):
        return (
            int(r) if r.isdigit() else pd.to_numeric(pd.Series([r]), errors="coerce")[0]
        )

    entries = []
    for title, pg in pattern.findall(text):
        try:
            page = roman_to_int(pg.strip())
            entries.append((title.strip(), int(page)))
        except:
            continue
    return entries


def parse_toc_auto(pdf_path):
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    toc_start = None
    # Find the page containing "Índice general"
    for i in range(total_pages):
        text = reader.pages[i].extract_text() or ""
        if "Índice general" in text:
            toc_start = i
            break
    if toc_start is None:
        return []

    # Extract text from toc_start to toc_start + 3 or end
    end_page = min(toc_start + 4, total_pages)
    combined_text = "\n".join(
        reader.pages[i].extract_text() or "" for i in range(toc_start, end_page)
    )
    pattern = re.compile(r"^(.*?)\s*(?:\.\s*){3,}(\d+|[IVXLCDM]+)\s*$", re.MULTILINE)

    def roman_to_int(r):
        r = r.upper()
        roman_numerals = {
            "I": 1,
            "V": 5,
            "X": 10,
            "L": 50,
            "C": 100,
            "D": 500,
            "M": 1000,
        }
        if r.isdigit():
            return int(r)
        total = 0
        prev_value = 0
        for char in reversed(r):
            value = roman_numerals.get(char, 0)
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value
        return total

    entries = []

    for title, pg in pattern.findall(combined_text):
        try:
            page_num = roman_to_int(pg.strip())
            entries.append((title.strip(), page_num))
        except:
            continue
    return entries


def extract_chapters(pdf_path, toc_entries):
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    # Sort entries by start page
    toc_entries = sorted(toc_entries, key=lambda x: x[1])
    chapters = []
    for i, (title, start) in enumerate(toc_entries):
        end = (toc_entries[i + 1][1] - 1) if i + 1 < len(toc_entries) else total_pages
        # Extract text
        pages_text = []
        for p in range(start - 1, end):
            pages_text.append(reader.pages[p].extract_text() or "")
        chapters.append(
            {
                "title": title,
                "start_page": start,
                "end_page": end,
                "text": "\n".join(pages_text),
            }
        )
    return pd.DataFrame(chapters)


def generate_json(pdf_path, title, author, publication_year):
    toc_entries = parse_toc_auto(pdf_path)
    if not toc_entries:
        raise ValueError("No TOC entries found.")

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    # Build page_number_map by scanning each page for rendered page number
    page_number_map = {}
    page_number_pattern = re.compile(r"^\s*(\d+)\s*$")
    for i in range(total_pages):
        text = reader.pages[i].extract_text() or ""
        lines = text.splitlines()
        candidates = []
        if lines:
            # Check first line
            if page_number_pattern.match(lines[0]):
                candidates.append(int(lines[0].strip()))
            # Check last line
            if len(lines) > 1 and page_number_pattern.match(lines[-1]):
                candidates.append(int(lines[-1].strip()))
        if candidates:
            # Prefer last line if both present
            page_number_map[candidates[-1]] = i

    sections = []
    current_section = None

    section_pattern = re.compile(r"^Sección\s+(\d+)—(.+)$")

    # Sort toc_entries by page number
    toc_entries = sorted(toc_entries, key=lambda x: x[1])

    for i, (entry_title, entry_page) in enumerate(toc_entries):
        match = section_pattern.match(entry_title)
        if match:
            # Close previous section if exists
            if current_section is not None:
                # Set end page of previous section to one less than current section start page, converted using page_number_map
                prev_end_page = entry_page - 1
                current_section["page_end"] = page_number_map.get(
                    prev_end_page, prev_end_page - 1
                )
                sections.append(current_section)
            section_number = int(match.group(1))
            section_title = match.group(2).strip()
            current_section = {
                "section_number": section_number,
                "section_title": section_title,
                "page_start": entry_page,
                "page_end": None,  # to be set later
                "items": [],
            }
        else:
            if current_section is None:
                # If no section yet, create a default one with section_number 0
                current_section = {
                    "section_number": 0,
                    "section_title": "",
                    "page_start": entry_page,
                    "page_end": None,
                    "items": [],
                }
            current_section["items"].append(
                {"title": entry_title, "page": entry_page, "content": ""}
            )

    # After loop ends, close last section
    if current_section is not None:
        # Set page_end to last PDF index
        if page_number_map:
            last_pdf_index = max(page_number_map.values())
        else:
            last_pdf_index = total_pages - 1
        current_section["page_end"] = last_pdf_index
        sections.append(current_section)

    # Fill each item's "content" by extracting text between its start_page and the next item/section boundary
    for section in sections:
        for idx, item in enumerate(section["items"]):
            # Determine start_idx
            start_idx = page_number_map.get(item["page"])
            if start_idx is None:
                # Search all pages for the title string
                found_idx = None
                title_to_find = item["title"]
                for page_idx in range(total_pages):
                    page_text = reader.pages[page_idx].extract_text() or ""
                    if title_to_find in page_text:
                        found_idx = page_idx
                        break
                if found_idx is not None:
                    start_idx = found_idx
                else:
                    # Could not find page by map or text search
                    item["content"] = ""
                    continue

            if idx + 1 < len(section["items"]):
                next_page = section["items"][idx + 1]["page"]
                end_idx = page_number_map.get(next_page, next_page - 1)
            else:
                end_idx = page_number_map.get(section["page_end"], total_pages)

            if end_idx <= start_idx:
                end_idx = start_idx + 1

            pages_text = []
            for p in range(start_idx, end_idx):
                pages_text.append(reader.pages[p].extract_text() or "")

            full_block = "\n".join(pages_text).strip()
            content = full_block
            # Clean both the title and the beginning of the content before comparing
            cleaned_title = item["title"].strip(" \n–—")
            trimmed_content = content.lstrip(" \n–—")
            if trimmed_content[: len(cleaned_title)].lower() == cleaned_title.lower():
                content = trimmed_content[len(cleaned_title) :].lstrip(" \n–—")
            clean_title = re.sub(r"[^A-Za-z0-9]+", "", title).strip()
            clean_author = re.sub(r"[^A-Za-z0-9]+", "", author).strip()
            item["book-section-id"] = (
                f"{clean_title}-{clean_author}-{item['page']}-{uuid.uuid4().hex[:8]}"
            )
            # Normalize paragraph linebreaks
            item["content"] = normalize_paragraphs(content)

    # After normalizing content for every original item, split into paragraph-level items
    for section in sections:
        para_items = []
        for item in section["items"]:
            full_text = item["content"]
            # split on double-newline paragraph boundaries
            paragraphs = full_text.split("\n\n") if full_text else []
            for idx, para in enumerate(paragraphs):
                # copy the item metadata except content
                new_item = {k: v for k, v in item.items() if k != "content"}
                # assign this paragraph as content
                new_item["content"] = para.strip()
                # track paragraph index
                new_item["paragraph_index"] = idx + 1
                para_items.append(new_item)
        # replace the original items list
        section["items"] = para_items

    data = {
        "title": title,
        "author": author,
        "publication_year": publication_year,
        "sections": sections,
    }

    base, _ = os.path.splitext(os.path.basename(pdf_path))
    out_dir = f"{base}_chapters"
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(os.path.dirname(out_dir), f"{base}.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    generate_json(
        "app/data/books/conflicto_de_los_siglos.pdf",
        "El Conflicto de los Siglos",
        "Ellen G. White",
        2007,
    )
