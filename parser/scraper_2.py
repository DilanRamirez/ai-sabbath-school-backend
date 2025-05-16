import re
import os
import json
import uuid
import pandas as pd
from PyPDF2 import PdfReader
import json


def parse_toc_format_1(pdf_path):
    reader = PdfReader(pdf_path)
    print(f"Number of pages: {len(reader.pages)}")
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
        reader.pages[i].extract_text() or "" for i in range(min(30, len(reader.pages)))
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
        if "Índice general" in text or "Contenido" in text:
            toc_start = i
            break
    if toc_start is None:
        return []

    # Extract text from toc_start to toc_start + 20 or end
    end_page = min(toc_start + 20, total_pages)
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
    print(f"TOC entries: {toc_entries}")
    if not toc_entries:
        raise ValueError("No TOC entries found.")

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"Total pages in PDF: {total_pages}")

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
            print(
                f"Processing item: {idx}, item: {item}, start: {section['page_start']}, end: {section['page_end']}"
            )
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

            # Use the section's printed start page to anchor the actual start index.
            section_start_idx = page_number_map.get(
                section["page_start"], section["page_start"] - 1
            )

            # Instead of solely relying on the printed page number mapping,
            # scan forward from the section start until we find the title text.
            candidate_idx = None
            for p in range(section_start_idx, total_pages):
                page_text = reader.pages[p].extract_text() or ""
                if item["title"] in page_text:
                    candidate_idx = p
                    break
            start_idx = (
                candidate_idx if candidate_idx is not None else section_start_idx
            )

            # For the end index, if there's a following item, try to detect its title in the pages.
            if idx + 1 < len(section["items"]):
                next_item = section["items"][idx + 1]
                candidate_end_idx = None
                for p in range(start_idx + 1, total_pages):
                    page_text = reader.pages[p].extract_text() or ""
                    if next_item["title"] in page_text:
                        candidate_end_idx = p
                        break
                end_idx = (
                    candidate_end_idx
                    if candidate_end_idx is not None
                    else page_number_map.get(next_item["page"], next_item["page"] - 1)
                )
            else:
                end_idx = page_number_map.get(section["page_end"], total_pages)

            if end_idx <= start_idx:
                end_idx = start_idx + 1

            print(
                f"Extracting content for '{item['title']}' from pages {start_idx} to {end_idx}"
            )

            pages_text = []
            section_header_pattern = re.compile(r"^Sección\s+\d+—", re.MULTILINE)
            for p in range(start_idx, end_idx):
                page_text = reader.pages[p].extract_text() or ""
                # In the first page, start extracting after the subheader's occurrence.
                if p == start_idx:
                    header_index = page_text.find(item["title"])
                    if header_index != -1:
                        page_text = page_text[header_index + len(item["title"]) :]
                # If the next subheader occurs on this page, only include text up to it.
                if idx + 1 < len(section["items"]):
                    next_header = section["items"][idx + 1]["title"]
                    next_index = page_text.find(next_header)
                    if next_index != -1:
                        page_text = page_text[:next_index]
                        pages_text.append(page_text)
                        break
                # If a new section header is detected, only include text up to its start.
                new_section_match = section_header_pattern.search(page_text)
                if new_section_match:
                    page_text = page_text[: new_section_match.start()]
                    pages_text.append(page_text)
                    break
                pages_text.append(page_text)
            item["content"] = "\n".join(pages_text)
            # Print first 100 chars
            print(f"Extracted content: {item['content'][:100]}...")
            print("---" * 30)

            # Clean up the title and author for book-section-id
            # Remove special characters and spaces
            # Clean both the title and the beginning of the content before comparing
            cleaned_title = item["title"].strip(" \n–—")
            trimmed_content = item["content"].lstrip(" \n–—")
            # Check if the cleaned title is at the start of the content
            if trimmed_content.startswith(cleaned_title):
                trimmed_content = trimmed_content[len(cleaned_title) :].lstrip(" \n–—")
            # Clean the title and author for book-section-id
            # Remove special characters and spaces
            # Clean both the title and the beginning of the content before comparing

            clean_title = re.sub(r"[^A-Za-z0-9]+", "", title).strip()
            clean_author = re.sub(r"[^A-Za-z0-9]+", "", author).strip()
            item["book-section-id"] = (
                f"{clean_title}-{clean_author}-{item['page']}-{uuid.uuid4().hex[:8]}"
            )

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

    print(f"JSON file created at {json_path}")


if __name__ == "__main__":
    generate_json(
        "app/data/books/Consejos_Sobre_el_Regimen_Alimenticio.pdf",
        "Consejos Sobre el Régimen Alimenticio",
        "Ellen G. White",
        1977,
    )
